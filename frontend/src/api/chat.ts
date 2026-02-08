import { apiFetch, getApiBase, triggerLogout } from "./client";
import type { Conversation } from "@/types/chat";

/** Backend message shape (has extra fields beyond our Message type) */
interface BackendMessage {
  id: string;
  conversation_id: string;
  user_id: string;
  role: string;
  content: string;
  created_at: string;
}

/**
 * Get all conversations for the authenticated user.
 */
export async function getConversations(): Promise<Conversation[]> {
  const res = await apiFetch("/chat/conversations");
  if (!res.ok) throw new Error("Failed to load conversations");
  return res.json();
}

/**
 * Get all messages in a conversation.
 */
export async function getMessages(conversationId: string): Promise<BackendMessage[]> {
  const res = await apiFetch(`/chat/conversations/${conversationId}/messages`);
  if (!res.ok) throw new Error("Failed to load messages");
  return res.json();
}

/**
 * Callback types for SSE events
 */
export interface StreamCallbacks {
  onToken: (content: string) => void;
  onToolStart: (tool: string) => void;
  onToolEnd: (tool: string) => void;
  onToolStatus: (message: string) => void;
  onDone: (conversationId: string) => void;
  onError: (error: string) => void;
}

/**
 * Send a message and stream the AI response via SSE.
 * Returns an AbortController so the caller can cancel the stream.
 */
export function streamChat(
  message: string,
  conversationId: string | null,
  callbacks: StreamCallbacks
): AbortController {
  const controller = new AbortController();
  const token = localStorage.getItem("access_token");
  const apiBase = getApiBase();

  fetch(`${apiBase}/chat/send`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
    }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (res.status === 401) {
        triggerLogout();
        return;
      }
      if (!res.ok) {
        callbacks.onError("Failed to send message");
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        callbacks.onError("No response stream");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const data = line.slice(6);
            try {
              const parsed = JSON.parse(data);
              switch (currentEvent) {
                case "token":
                  callbacks.onToken(parsed.content);
                  break;
                case "tool_start":
                  callbacks.onToolStart(parsed.tool);
                  break;
                case "tool_end":
                  callbacks.onToolEnd(parsed.tool);
                  break;
                case "tool_status":
                  callbacks.onToolStatus(parsed.message);
                  break;
                case "done":
                  callbacks.onDone(parsed.conversation_id);
                  break;
              }
            } catch {
              // skip malformed JSON
            }
            currentEvent = "";
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        callbacks.onError(err.message || "Stream error");
      }
    });

  return controller;
}
