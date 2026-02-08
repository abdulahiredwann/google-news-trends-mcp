import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getConversations } from "@/api/chat";
import type { Conversation } from "@/types/chat";

interface SidebarProps {
  currentConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onClose: () => void;
  refreshKey: number;
}

function SidebarSkeleton() {
  return (
    <div className="space-y-2 px-1">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="rounded-lg px-3 py-2.5 space-y-1.5">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-3 w-16" />
        </div>
      ))}
    </div>
  );
}

export default function Sidebar({
  currentConversationId,
  onSelectConversation,
  onNewChat,
  onClose,
  refreshKey,
}: SidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [initialLoad, setInitialLoad] = useState(true);

  useEffect(() => {
    let cancelled = false;

    getConversations()
      .then((data) => {
        if (!cancelled) setConversations(data);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setInitialLoad(false);
      });

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const handleSelect = (id: string) => {
    onSelectConversation(id);
    // Close sidebar on mobile after selecting
    onClose();
  };

  const handleNewChat = () => {
    onNewChat();
    onClose();
  };

  return (
    <>
      {/* Backdrop — mobile only: blurred overlay behind sidebar */}
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm md:hidden"
        onClick={onClose}
      />

      {/* Sidebar panel */}
      <div className="fixed inset-y-0 left-0 z-50 flex w-[calc(100%-3rem)] max-w-xs flex-col overflow-hidden border-r bg-background md:static md:z-auto md:w-64 md:max-w-none">
        {/* Header with close button (mobile) */}
        <div className="flex items-center justify-between p-3">
          <Button
            onClick={handleNewChat}
            className="flex-1 justify-start gap-2"
            variant="outline"
          >
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
            >
              <path d="M12 5v14" />
              <path d="M5 12h14" />
            </svg>
            New Chat
          </Button>
          {/* Close button — mobile only */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="ml-2 h-8 w-8 p-0 md:hidden"
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
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </Button>
        </div>

        {/* Conversations List */}
        <div className="flex-1 min-h-0 overflow-y-auto px-2">
          {initialLoad && conversations.length === 0 && <SidebarSkeleton />}

          {!initialLoad && conversations.length === 0 && (
            <div className="px-3 py-4 text-center text-sm text-muted-foreground">
              No conversations yet
            </div>
          )}

          {conversations.length > 0 && (
            <div className="space-y-1 pb-2">
              {conversations.map((conv) => {
                const isActive = conv.id === currentConversationId;
                return (
                  <button
                    key={conv.id}
                    onClick={() => handleSelect(conv.id)}
                    className={`group flex w-full flex-col items-start gap-0.5 rounded-lg px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted ${
                      isActive
                        ? "bg-muted font-medium"
                        : "text-muted-foreground"
                    }`}
                  >
                    <span className="line-clamp-1 w-full">{conv.title}</span>
                    <span className="text-xs text-muted-foreground/70">
                      {formatDate(conv.updated_at)}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
