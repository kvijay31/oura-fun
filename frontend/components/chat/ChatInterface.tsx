"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { streamChat, type ChatMessage } from "@/lib/api";
import { ChatMessage as ChatMessageComponent, type MessageItem } from "./ChatMessage";
import { ChatInput } from "./ChatInput";

const SUGGESTIONS = [
  "How was my sleep last week?",
  "What's my readiness trend this month?",
  "Compare my sleep score vs activity score for the past 30 days",
  "When was my HRV highest in the last 90 days?",
];

let messageCounter = 0;
function nextId() {
  return `msg-${++messageCounter}`;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  // Scroll to bottom when messages update
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [messages]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming) return;

    setInput("");

    const userMsg: MessageItem = {
      id: nextId(),
      role: "user",
      content: text,
    };

    const assistantId = nextId();
    const assistantMsg: MessageItem = {
      id: assistantId,
      role: "assistant",
      content: "",
      toolCalls: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    // Build history for API (exclude the blank streaming placeholder)
    const history: ChatMessage[] = messages
      .filter((m) => m.content || m.role === "user")
      .map((m) => ({ role: m.role, content: m.content }));
    history.push({ role: "user", content: text });

    let aborted = false;
    abortRef.current = () => {
      aborted = true;
    };

    try {
      for await (const event of streamChat(history)) {
        if (aborted) break;

        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== assistantId) return m;

            switch (event.type) {
              case "text":
                return { ...m, content: m.content + event.text };

              case "tool_start":
                return {
                  ...m,
                  toolCalls: [
                    ...(m.toolCalls ?? []),
                    {
                      id: `tc-${Date.now()}`,
                      name: event.name,
                      status: "start" as const,
                    },
                  ],
                };

              case "tool_running":
                return {
                  ...m,
                  toolCalls: (m.toolCalls ?? []).map((tc) =>
                    tc.name === event.name && tc.status === "start"
                      ? {
                          ...tc,
                          status: "running" as const,
                          input: event.input,
                        }
                      : tc
                  ),
                };

              case "tool_done":
                return {
                  ...m,
                  toolCalls: (m.toolCalls ?? []).map((tc) =>
                    tc.name === event.name && tc.status === "running"
                      ? { ...tc, status: "done" as const }
                      : tc
                  ),
                };

              case "done":
                return { ...m, isStreaming: false };

              case "error":
                return {
                  ...m,
                  content: m.content
                    ? m.content
                    : `Error: ${event.message}`,
                  isStreaming: false,
                };

              default:
                return m;
            }
          })
        );
      }
    } catch (err) {
      if (!aborted) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: `Connection error: ${err instanceof Error ? err.message : String(err)}`,
                  isStreaming: false,
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
      // Ensure streaming flag is cleared even if done event wasn't received
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, isStreaming: false } : m))
      );
    }
  }, [input, isStreaming, messages]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full">
      {/* Message thread */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-6 space-y-1"
      >
        {isEmpty ? (
          <EmptyState onSuggestion={(s) => { setInput(s); }} />
        ) : (
          messages.map((msg) => (
            <ChatMessageComponent key={msg.id} message={msg} />
          ))
        )}
      </div>

      {/* Input area */}
      <div className="flex-none px-4 pb-6">
        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={sendMessage}
          disabled={isStreaming}
        />
        <p className="text-center text-ink-muted text-xs mt-3">
          Queries your local Oura DuckDB via the MCP server &middot; data never leaves your machine
        </p>
      </div>
    </div>
  );
}

function EmptyState({ onSuggestion }: { onSuggestion: (s: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6 py-12 gap-8">
      <div>
        <div className="w-12 h-12 rounded-full bg-chat-dim border border-chat/20 flex items-center justify-center mx-auto mb-4">
          <OuraLogo />
        </div>
        <h2 className="text-xl font-semibold text-ink-primary mb-2">
          Ask about your health data
        </h2>
        <p className="text-ink-secondary text-sm max-w-xs leading-relaxed">
          I can query your sleep, readiness, and activity data using the Oura MCP tools.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSuggestion(s)}
            className="text-left px-4 py-3 rounded-xl bg-bg-surface border border-edge
              text-sm text-ink-secondary hover:text-ink-primary hover:border-edge-hover
              hover:bg-bg-elevated transition-all duration-base text-pretty"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

function OuraLogo() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
      <circle cx="11" cy="11" r="9" stroke="#A78BFA" strokeWidth="2" />
      <circle cx="11" cy="11" r="3.5" fill="#A78BFA" />
    </svg>
  );
}
