"use client";

import { useRefresh } from "@/lib/refresh-context";

function timeAgo(isoStr: string): string {
  const diff = Date.now() - new Date(isoStr).getTime();
  const min = Math.round(diff / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const h = Math.floor(min / 60);
  return `${h}h ago`;
}

const baseText: React.CSSProperties = {
  fontSize: 12,
  color: "var(--text-muted)",
};

export default function RefreshBadge() {
  const { refreshState, lastRefreshed, trigger } = useRefresh();

  const timestamps = Object.values(lastRefreshed).filter((v): v is string => !!v);
  const latestTs = timestamps.length > 0 ? timestamps.sort().at(-1) : null;

  if (refreshState === "unavailable") return null;

  if (refreshState === "refreshing") {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <RefreshSpinner />
        <span style={baseText}>Refreshing…</span>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      {latestTs && (
        <span style={baseText}>Updated {timeAgo(latestTs)}</span>
      )}
      <button
        onClick={trigger}
        title="Refresh data"
        style={{
          background: "transparent",
          border: "none",
          padding: "4px 6px",
          borderRadius: 6,
          cursor: "pointer",
          color: "var(--text-muted)",
          fontSize: 14,
          lineHeight: 1,
          transition: "color 0.15s, background 0.15s",
          display: "flex",
          alignItems: "center",
        }}
        onMouseEnter={e => {
          (e.currentTarget as HTMLButtonElement).style.color = "var(--text-secondary)";
          (e.currentTarget as HTMLButtonElement).style.background = "var(--bg-overlay)";
        }}
        onMouseLeave={e => {
          (e.currentTarget as HTMLButtonElement).style.color = "var(--text-muted)";
          (e.currentTarget as HTMLButtonElement).style.background = "transparent";
        }}
      >
        ↻
      </button>
    </div>
  );
}

function RefreshSpinner() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      style={{ animation: "spin 0.9s linear infinite" }}
    >
      <circle cx="7" cy="7" r="5.5" stroke="var(--text-muted)" strokeWidth="1.5" strokeDasharray="22 8" strokeLinecap="round" />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </svg>
  );
}
