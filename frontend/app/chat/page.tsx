import Link from "next/link";
import { ChatInterface } from "@/components/chat/ChatInterface";

export const metadata = {
  title: "Chat — Oura Fun",
};

export default function ChatPage() {
  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto">
      {/* Header */}
      <header className="flex-none flex items-center justify-between px-5 py-4 border-b border-edge">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="text-ink-muted hover:text-ink-secondary transition-colors duration-fast"
            aria-label="Home"
          >
            <HomeIcon />
          </Link>
          <div className="w-px h-4 bg-edge" />
          <span className="text-sm font-medium text-ink-primary">Chat</span>
        </div>

        <div className="flex items-center gap-2">
          <MetricPip color="var(--color-readiness)" label="R" />
          <MetricPip color="var(--color-sleep)" label="S" />
          <MetricPip color="var(--color-activity)" label="A" />
        </div>
      </header>

      {/* Chat interface fills remaining height */}
      <ChatInterface />
    </div>
  );
}

function MetricPip({ color, label }: { color: string; label: string }) {
  return (
    <div
      className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold"
      style={{ background: `${color}22`, color, border: `1px solid ${color}44` }}
    >
      {label}
    </div>
  );
}

function HomeIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
      <path
        d="M2 7l6-5 6 5v7a1 1 0 01-1 1H3a1 1 0 01-1-1V7z"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinejoin="round"
      />
      <path
        d="M6 14V9h4v5"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinejoin="round"
      />
    </svg>
  );
}
