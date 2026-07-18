"use client";

import { useRef, useEffect, KeyboardEvent } from "react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled,
  placeholder = "Ask about your sleep, readiness, or activity…",
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && value.trim()) onSubmit();
    }
  }

  return (
    <div
      className="flex items-end gap-3 px-4 py-3 bg-bg-surface border border-edge rounded-2xl
        focus-within:border-edge-focus transition-colors duration-base"
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKey}
        disabled={disabled}
        placeholder={placeholder}
        rows={1}
        className="flex-1 resize-none bg-transparent text-sm text-ink-primary
          placeholder:text-ink-muted outline-none leading-relaxed
          min-h-[24px] max-h-[160px] py-0.5"
      />
      <button
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        aria-label="Send"
        className="flex-none w-8 h-8 rounded-full flex items-center justify-center
          bg-chat text-white
          disabled:opacity-30 disabled:cursor-not-allowed
          hover:opacity-90 active:scale-95
          transition-all duration-fast"
      >
        <SendIcon />
      </button>
    </div>
  );
}

function SendIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path
        d="M12 7L2 2.5l1.5 4.5L2 11.5 12 7z"
        fill="currentColor"
      />
    </svg>
  );
}
