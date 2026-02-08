import { useState, useRef, useEffect, useCallback } from "react";
import type { FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/state/auth";
import { streamChat, getMessages } from "@/api/chat";
import Sidebar from "@/components/Sidebar";
import ThemeToggle from "@/components/ThemeToggle";
import type { Message } from "@/types/chat";

/**
 * Maps raw tool names from the backend to user-friendly display labels.
 * The docs require: "Searching web…", "Fetching trends…" style indicators.
 */
const TOOL_LABELS: Record<string, string> = {
  tavily_search:        "Searching the web",
  get_trending_terms:   "Fetching trending terms",
  get_news_by_keyword:  "Searching Google News",
  get_news_by_location: "Searching news by location",
  get_news_by_topic:    "Searching news by topic",
  get_top_news:         "Fetching top news",
};

function getToolLabel(tool: string): string {
  return TOOL_LABELS[tool] || `Using ${tool.replace(/_/g, " ")}`;
}

const WELCOME_MESSAGE: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Hello! I can help you search the web, check Google Trends, and more. What would you like to know?",
};

export default function ChatPage() {
  const { logout, user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [toolActivity, setToolActivity] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(() => {
    return localStorage.getItem("current_conversation_id");
  });
  const [isRestoring, setIsRestoring] = useState(false);
  const [sidebarRefreshKey, setSidebarRefreshKey] = useState(0);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // On desktop, open sidebar by default
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    setSidebarOpen(mq.matches);
    const handler = (e: MediaQueryListEvent) => setSidebarOpen(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Load messages for a given conversation
  const loadConversation = useCallback(async (convId: string) => {
    setIsRestoring(true);
    try {
      const storedMessages = await getMessages(convId);
      if (storedMessages.length > 0) {
        const restored: Message[] = storedMessages.map((m) => ({
          id: m.id || crypto.randomUUID(),
          role: m.role as "user" | "assistant",
          content: m.content,
        }));
        setMessages([WELCOME_MESSAGE, ...restored]);
      } else {
        setMessages([WELCOME_MESSAGE]);
      }
    } catch {
      console.warn("Could not load conversation");
      setMessages([WELCOME_MESSAGE]);
    } finally {
      setIsRestoring(false);
    }
  }, []);

  // Restore chat history on mount
  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Save conversationId to localStorage whenever it changes
  useEffect(() => {
    if (conversationId) {
      localStorage.setItem("current_conversation_id", conversationId);
    } else {
      localStorage.removeItem("current_conversation_id");
    }
  }, [conversationId]);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, toolActivity]);

  // Switch to an existing conversation
  const handleSelectConversation = useCallback(
    (convId: string) => {
      if (convId === conversationId) return;
      abortRef.current?.abort();
      setIsLoading(false);
      setToolActivity("");
      setConversationId(convId);
      loadConversation(convId);
    },
    [conversationId, loadConversation]
  );

  // Start a new conversation
  const handleNewChat = useCallback(() => {
    abortRef.current?.abort();
    setConversationId(null);
    setMessages([WELCOME_MESSAGE]);
    setIsLoading(false);
    setToolActivity("");
  }, []);

  const handleSend = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userText = input.trim();

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: userText,
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setToolActivity("");

    const assistantId = (Date.now() + 1).toString();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "" },
    ]);

    const controller = streamChat(userText, conversationId, {
      onToken: (content) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: m.content + content }
              : m
          )
        );
      },
      onToolStart: (tool) => {
        setToolActivity(getToolLabel(tool));
      },
      onToolEnd: () => {
        setToolActivity("");
      },
      onToolStatus: (message) => {
        setToolActivity(message);
        setTimeout(() => setToolActivity(""), 4000);
      },
      onDone: (convId) => {
        setConversationId(convId);
        setIsLoading(false);
        setToolActivity("");
        setSidebarRefreshKey((k) => k + 1);
      },
      onError: (error) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: m.content || `Error: ${error}` }
              : m
          )
        );
        setIsLoading(false);
        setToolActivity("");
      },
    });

    abortRef.current = controller;
  };

  const handleLogout = () => {
    abortRef.current?.abort();
    localStorage.removeItem("current_conversation_id");
    logout();
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      {sidebarOpen && (
        <Sidebar
          currentConversationId={conversationId}
          onSelectConversation={handleSelectConversation}
          onNewChat={handleNewChat}
          onClose={() => setSidebarOpen(false)}
          refreshKey={sidebarRefreshKey}
        />
      )}

      {/* Main Chat Area */}
      <div className="flex flex-1 flex-col min-h-0 overflow-hidden">
        {/* Header */}
        <header className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="h-8 w-8 p-0"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                <line x1="9" x2="9" y1="3" y2="21" />
              </svg>
            </Button>
            <h1 className="text-lg font-semibold">AI Chat Agent</h1>
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />

            {/* User Profile Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 rounded-full p-0">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                      {user?.email?.charAt(0).toUpperCase() || "U"}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col gap-1">
                    <p className="text-sm font-medium">Account</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {user?.email}
                    </p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive cursor-pointer">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="mr-2"
                  >
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" x2="9" y1="12" y2="12" />
                  </svg>
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4">
          <div className="mx-auto max-w-3xl space-y-4">
            {isRestoring && (
              <div className="space-y-4">
                <div className="flex gap-3">
                  <Skeleton className="h-8 w-8 rounded-full shrink-0" />
                  <div className="space-y-2 flex-1 max-w-[65%]">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                  </div>
                </div>
                <div className="flex gap-3 flex-row-reverse">
                  <Skeleton className="h-8 w-8 rounded-full shrink-0" />
                  <div className="space-y-2 max-w-[50%]">
                    <Skeleton className="h-4 w-full" />
                  </div>
                </div>
                <div className="flex gap-3">
                  <Skeleton className="h-8 w-8 rounded-full shrink-0" />
                  <div className="space-y-2 flex-1 max-w-[70%]">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-5/6" />
                    <Skeleton className="h-4 w-2/3" />
                  </div>
                </div>
                <div className="flex gap-3 flex-row-reverse">
                  <Skeleton className="h-8 w-8 rounded-full shrink-0" />
                  <div className="space-y-2 max-w-[40%]">
                    <Skeleton className="h-4 w-full" />
                  </div>
                </div>
                <div className="flex gap-3">
                  <Skeleton className="h-8 w-8 rounded-full shrink-0" />
                  <div className="space-y-2 flex-1 max-w-[60%]">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-4/5" />
                  </div>
                </div>
              </div>
            )}

            {!isRestoring && messages.map((msg) => {
              // Hide the empty assistant bubble while loading —
              // we show the activity indicator below instead
              if (!msg.content && msg.role === "assistant" && isLoading) {
                return null;
              }

              return (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${
                    msg.role === "user" ? "flex-row-reverse" : "flex-row"
                  }`}
                >
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback
                      className={
                        msg.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }
                    >
                      {msg.role === "user" ? "U" : "AI"}
                    </AvatarFallback>
                  </Avatar>
                  <div
                    className={`max-w-[75%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              );
            })}

            {/* Activity Indicator — "Thinking…" or tool label while waiting */}
            {isLoading && (() => {
              const last = messages[messages.length - 1];
              const pendingResponse = last && last.role === "assistant" && !last.content;
              if (!pendingResponse) return null;
              return (
                <div className="flex items-center gap-3">
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-muted">AI</AvatarFallback>
                  </Avatar>
                  <div className="flex items-center gap-2.5 rounded-lg bg-muted px-4 py-2.5 text-sm text-muted-foreground">
                    <span className="relative flex h-2 w-2 shrink-0">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                    </span>
                    {toolActivity ? `${toolActivity}…` : "Thinking…"}
                  </div>
                </div>
              );
            })()}

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t px-4 py-3">
          <form
            onSubmit={handleSend}
            className="mx-auto flex max-w-3xl gap-2"
          >
            <Input
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading || isRestoring}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={isLoading || isRestoring || !input.trim()}
            >
              Send
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
