"use client";

import type { ChatMessage as Msg, StreamEvent } from "@/lib/api";
import { ToolCallBadge } from "./ToolCallBadge";

interface ToolCall {
  id: string;
  name: string;
  status: "start" | "running" | "done";
  input?: Record<string, unknown>;
}

export interface MessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
}

interface ChatMessageProps {
  message: MessageItem;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex justify-end px-4 py-1 animate-slide-up">
        <div
          className="max-w-[75%] px-4 py-3 rounded-2xl rounded-br-sm
            bg-bg-elevated border border-edge text-ink-primary text-sm leading-relaxed"
        >
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 px-4 py-1 animate-slide-up">
      {/* Avatar */}
      <div
        className="flex-none w-7 h-7 rounded-full flex items-center justify-center mt-0.5
          bg-chat-dim border border-chat/20"
      >
        <OuraIcon />
      </div>

      <div className="flex-1 min-w-0">
        {/* Tool calls above the message */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {message.toolCalls.map((tc) => (
              <ToolCallBadge
                key={tc.id}
                name={tc.name}
                status={tc.status}
                input={tc.input}
              />
            ))}
          </div>
        )}

        {/* Message content */}
        {message.content && (
          <div className="text-sm text-ink-primary prose-chat">
            <FormattedText text={message.content} />
          </div>
        )}

        {/* Streaming cursor */}
        {message.isStreaming && !message.content && (
          <div className="flex gap-1 items-center h-5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-ink-muted animate-pulse-dot"
                style={{ animationDelay: `${i * 0.16}s` }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function FormattedText({ text }: { text: string }) {
  // Render newlines as paragraphs for readability
  const paragraphs = text.split(/\n\n+/);
  if (paragraphs.length === 1) {
    return <p className="whitespace-pre-wrap">{text}</p>;
  }
  return (
    <>
      {paragraphs.map((p, i) => (
        <p key={i} className="mb-3 last:mb-0 whitespace-pre-wrap">
          {p}
        </p>
      ))}
    </>
  );
}

function OuraIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="5.5" stroke="#A78BFA" strokeWidth="1.5" />
      <circle cx="7" cy="7" r="2" fill="#A78BFA" />
    </svg>
  );
}
