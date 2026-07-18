"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import NavShell from "@/components/NavShell";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ToolCall {
  name: string;
  input: Record<string, unknown>;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  streaming?: boolean;
  error?: boolean;
}

const TOOL_ICONS: Record<string, string> = {
  query_sleep: "🌙",
  query_readiness: "⚡",
  query_activity: "🏃",
  compare_people: "👥",
  baseline: "📊",
  run_sql: "🔍",
};

function ToolBadge({ name }: { name: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        background: "var(--bg-elevated)",
        border: "1px solid var(--border-subtle)",
        borderRadius: 6,
        padding: "2px 8px",
        fontSize: 11,
        color: "var(--text-muted)",
        fontFamily: "inherit",
      }}
    >
      {TOOL_ICONS[name] ?? "🔧"} {name}
    </span>
  );
}

function Cursor() {
  return (
    <span
      style={{
        display: "inline-block",
        width: 2,
        height: "1em",
        background: "var(--text-secondary)",
        marginLeft: 2,
        verticalAlign: "text-bottom",
        animation: "cursorBlink 1s step-end infinite",
      }}
    />
  );
}

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: isUser ? "flex-end" : "flex-start",
        gap: 6,
        maxWidth: "78%",
        alignSelf: isUser ? "flex-end" : "flex-start",
      }}
    >
      {msg.toolCalls && msg.toolCalls.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
          {msg.toolCalls.map((tc, i) => (
            <ToolBadge key={i} name={tc.name} />
          ))}
        </div>
      )}
      <div
        style={{
          background: isUser ? "var(--bg-overlay)" : "var(--bg-surface)",
          border: `1px solid ${isUser ? "var(--border-muted)" : "var(--border-subtle)"}`,
          borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
          padding: "11px 16px",
          fontSize: 14,
          lineHeight: 1.65,
          color: msg.error ? "#F87171" : "var(--text-primary)",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          boxShadow: isUser ? "none" : "0 2px 16px rgba(0,0,0,0.18)",
        }}
      >
        {msg.content || (msg.streaming && !msg.toolCalls?.length ? "" : "")}
        {msg.streaming && <Cursor />}
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  "How was my sleep last week?",
  "What's my readiness trend this month?",
  "Compare sleep scores across all people",
  "What's my HRV baseline for the last 90 days?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, [input]);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { role: "user", content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    // Build history for the API (role + content only)
    const history = newMessages.map((m) => ({ role: m.role, content: m.content }));

    // Placeholder streaming assistant message
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", streaming: true, toolCalls: [] },
    ]);

    try {
      const res = await fetch(`${BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });

      if (!res.ok || !res.body) {
        throw new Error(`Server returned ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          let payload: { type: string; delta?: string; name?: string; input?: Record<string, unknown>; message?: string };
          try {
            payload = JSON.parse(line.slice(6));
          } catch {
            continue;
          }

          if (payload.type === "text" && payload.delta) {
            setMessages((prev) => {
              const copy = [...prev];
              const last = copy[copy.length - 1];
              if (last?.role === "assistant") {
                copy[copy.length - 1] = { ...last, content: last.content + payload.delta! };
              }
              return copy;
            });
          } else if (payload.type === "tool_call" && payload.name) {
            setMessages((prev) => {
              const copy = [...prev];
              const last = copy[copy.length - 1];
              if (last?.role === "assistant") {
                copy[copy.length - 1] = {
                  ...last,
                  toolCalls: [...(last.toolCalls ?? []), { name: payload.name!, input: payload.input ?? {} }],
                };
              }
              return copy;
            });
          } else if (payload.type === "done") {
            setMessages((prev) => {
              const copy = [...prev];
              const last = copy[copy.length - 1];
              if (last?.role === "assistant") {
                copy[copy.length - 1] = { ...last, streaming: false };
              }
              return copy;
            });
          } else if (payload.type === "error") {
            setMessages((prev) => {
              const copy = [...prev];
              const last = copy[copy.length - 1];
              if (last?.role === "assistant") {
                copy[copy.length - 1] = {
                  ...last,
                  content: payload.message ?? "Unknown error",
                  streaming: false,
                  error: true,
                };
              }
              return copy;
            });
          }
        }
      }
    } catch (err) {
      setMessages((prev) => {
        const copy = [...prev];
        const last = copy[copy.length - 1];
        if (last?.role === "assistant") {
          copy[copy.length - 1] = {
            ...last,
            content: `Could not reach the API. Make sure the server is running on port 8000.`,
            streaming: false,
            error: true,
          };
        }
        return copy;
      });
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }, [input, loading, messages]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const canSend = input.trim().length > 0 && !loading;

  return (
    <>
      <style>{`
        @keyframes cursorBlink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
      <NavShell>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            height: "calc(100vh - 56px - 64px)",
            minHeight: 400,
          }}
        >
          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              display: "flex",
              flexDirection: "column",
              gap: 14,
              paddingBottom: 8,
              paddingRight: 2,
            }}
          >
            {messages.length === 0 && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 24,
                  marginTop: 60,
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 32 }}>💍</span>
                  <p style={{ color: "var(--text-secondary)", fontSize: 15, fontWeight: 600, margin: 0 }}>
                    Ask about your Oura Ring data
                  </p>
                  <p style={{ color: "var(--text-muted)", fontSize: 13, margin: 0 }}>
                    Powered by Claude — uses your local DuckDB data
                  </p>
                </div>
                <div
                  style={{
                    display: "flex",
                    flexWrap: "wrap",
                    gap: 8,
                    justifyContent: "center",
                    maxWidth: 520,
                  }}
                >
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => {
                        setInput(s);
                        textareaRef.current?.focus();
                      }}
                      style={{
                        background: "var(--bg-surface)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: 20,
                        padding: "8px 16px",
                        fontSize: 13,
                        color: "var(--text-secondary)",
                        cursor: "pointer",
                        fontFamily: "inherit",
                        transition: "border-color 0.15s, color 0.15s",
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <MessageBubble key={i} msg={msg} />
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-muted)",
              borderRadius: 18,
              padding: "10px 12px 10px 16px",
              display: "flex",
              alignItems: "flex-end",
              gap: 10,
              boxShadow: "0 0 40px rgba(0,0,0,0.25)",
              marginTop: 14,
              flexShrink: 0,
            }}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about sleep, readiness, activity…"
              disabled={loading}
              rows={1}
              style={{
                flex: 1,
                background: "transparent",
                border: "none",
                outline: "none",
                resize: "none",
                fontSize: 14,
                color: "var(--text-primary)",
                fontFamily: "inherit",
                lineHeight: 1.55,
                overflow: "hidden",
                paddingTop: 3,
                paddingBottom: 3,
              }}
            />
            <button
              onClick={send}
              disabled={!canSend}
              style={{
                background: canSend ? "#00D2FF" : "var(--bg-elevated)",
                color: canSend ? "#0B0D12" : "var(--text-muted)",
                border: "none",
                borderRadius: 10,
                width: 34,
                height: 34,
                cursor: canSend ? "pointer" : "not-allowed",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 16,
                fontWeight: 700,
                transition: "background 0.15s, color 0.15s",
                flexShrink: 0,
              }}
              aria-label="Send"
            >
              ↑
            </button>
          </div>
        </div>
      </NavShell>
    </>
  );
}
