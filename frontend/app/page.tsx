import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="text-center max-w-md">
        <div className="mb-8 flex justify-center gap-3">
          <ScoreRing color="#22D3EE" label="R" />
          <ScoreRing color="#6366F1" label="S" />
          <ScoreRing color="#F97316" label="A" />
        </div>
        <h1 className="text-4xl font-semibold tracking-tight text-ink-primary mb-3">
          Oura Fun
        </h1>
        <p className="text-ink-secondary text-base mb-10 leading-relaxed">
          Your Oura Ring data — locally hosted. Chat with your health data or
          explore the dashboard.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/chat"
            className="px-6 py-3 rounded-xl bg-chat text-white font-medium text-sm
              hover:opacity-90 transition-opacity duration-base shadow-glow-chat"
          >
            Open Chat
          </Link>
          <Link
            href="/dashboard"
            className="px-6 py-3 rounded-xl bg-bg-surface text-ink-primary font-medium text-sm
              border border-edge hover:border-edge-hover hover:bg-bg-elevated
              transition-all duration-base"
          >
            Dashboard
          </Link>
        </div>
        <p className="mt-8 text-ink-muted text-xs">
          Running locally — your data never leaves your machine.
        </p>
      </div>
    </main>
  );
}

function ScoreRing({ color, label }: { color: string; label: string }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  return (
    <div className="relative w-16 h-16">
      <svg viewBox="0 0 72 72" className="w-full h-full -rotate-90">
        <circle
          cx="36"
          cy="36"
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth="6"
        />
        <circle
          cx="36"
          cy="36"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeDasharray={circ}
          strokeDashoffset={circ * 0.28}
          strokeLinecap="round"
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center text-xs font-semibold"
        style={{ color }}
      >
        {label}
      </span>
    </div>
  );
}
