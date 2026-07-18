"use client";

import { useEffect, useRef } from "react";
import type { Metric } from "@/lib/tokens";

const METRIC_GRADIENTS: Record<Metric, { id: string; from: string; to: string; glow: string }> = {
  readiness: { id: "grad-readiness", from: "#00D2FF", to: "#006699", glow: "rgba(0,210,255,0.22)" },
  sleep: { id: "grad-sleep", from: "#818CF8", to: "#4338CA", glow: "rgba(129,140,248,0.22)" },
  activity: { id: "grad-activity", from: "#FB923C", to: "#EA580C", glow: "rgba(249,115,22,0.22)" },
};

interface RingScoreProps {
  score: number | null;
  metric: Metric;
  size?: number;
  label?: string;
}

export default function RingScore({ score, metric, size = 120, label }: RingScoreProps) {
  const { id, from, to, glow } = METRIC_GRADIENTS[metric];
  const strokeWidth = size * 0.09;
  const r = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;
  const pct = score != null ? Math.max(0, Math.min(100, score)) / 100 : 0;
  const offset = circumference * (1 - pct);

  const arcRef = useRef<SVGCircleElement>(null);
  const numRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const arc = arcRef.current;
    if (!arc || score == null) return;
    arc.style.transition = "none";
    arc.style.strokeDashoffset = String(circumference);
    arc.getBoundingClientRect();
    arc.style.transition = "stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)";
    arc.style.strokeDashoffset = String(offset);
  }, [score, circumference, offset]);

  useEffect(() => {
    const el = numRef.current;
    if (!el || score == null) return;
    let start = 0;
    const target = score;
    const dur = 1000;
    const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min((now - t0) / dur, 1);
      el.textContent = String(Math.round(start + (target - start) * p));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [score]);

  const trackColor = "rgba(255,255,255,0.06)";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        {/* Glow backdrop */}
        <div
          className="absolute inset-0 rounded-full pointer-events-none"
          style={{ boxShadow: `0 0 ${size * 0.4}px ${glow}`, borderRadius: "50%" }}
        />
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: "rotate(-90deg)" }}>
          <defs>
            <linearGradient id={id} x1="1" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={from} />
              <stop offset="100%" stopColor={to} />
            </linearGradient>
          </defs>
          {/* Track */}
          <circle
            cx={cx} cy={cy} r={r}
            fill="none"
            stroke={trackColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Fill arc */}
          <circle
            ref={arcRef}
            cx={cx} cy={cy} r={r}
            fill="none"
            stroke={`url(#${id})`}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={score == null ? circumference : offset}
          />
        </svg>
        {/* Score numeral */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            ref={numRef}
            style={{
              fontSize: size * 0.28,
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: "var(--text-primary)",
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {score ?? "–"}
          </span>
        </div>
      </div>
      {label && (
        <span style={{ color: "var(--text-secondary)", fontSize: 12, fontWeight: 500, letterSpacing: "0.04em", textTransform: "uppercase" }}>
          {label}
        </span>
      )}
    </div>
  );
}
