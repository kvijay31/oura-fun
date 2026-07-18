"use client";

import { formatToolName } from "@/lib/api";

interface ToolCallBadgeProps {
  name: string;
  status: "start" | "running" | "done";
  input?: Record<string, unknown>;
}

export function ToolCallBadge({ name, status, input }: ToolCallBadgeProps) {
  const label = formatToolName(name);

  return (
    <div
      className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
        bg-chat-dim text-chat border border-chat/20 my-1"
    >
      {status === "running" ? (
        <SpinnerDots />
      ) : status === "done" ? (
        <CheckIcon />
      ) : (
        <WandIcon />
      )}
      <span>{label}</span>
      {input && status !== "running" && Object.keys(input).length > 0 && (
        <span className="text-ink-muted font-normal">
          {formatInputSummary(input)}
        </span>
      )}
    </div>
  );
}

function formatInputSummary(input: Record<string, unknown>): string {
  const parts: string[] = [];
  if (input.person) parts.push(String(input.person));
  if (input.metric) parts.push(String(input.metric));
  if (input.start && input.end) {
    parts.push(`${input.start} – ${input.end}`);
  } else if (input.window) {
    parts.push(`${input.window}d`);
  }
  if (input.query) {
    const q = String(input.query);
    parts.push(q.length > 40 ? q.slice(0, 40) + "…" : q);
  }
  return parts.length ? `(${parts.join(", ")})` : "";
}

function SpinnerDots() {
  return (
    <span className="flex gap-0.5 items-center">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1 h-1 rounded-full bg-chat animate-pulse-dot"
          style={{ animationDelay: `${i * 0.16}s` }}
        />
      ))}
    </span>
  );
}

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path
        d="M2 6l3 3 5-5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function WandIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
      <path
        d="M7 2l3 3M2 10l6-6M9 1l2 2M1 9l2 2"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </svg>
  );
}
