/**
 * Design tokens — single source of truth for colors, spacing, radii, motion.
 * Dark-first Oura-style palette: deep navy backgrounds, soft gradient accents.
 */

export const colors = {
  bg: {
    base: "#0B0D12",
    surface: "#13161E",
    elevated: "#1A1E28",
    overlay: "#222736",
  },
  border: {
    subtle: "rgba(255,255,255,0.06)",
    muted: "rgba(255,255,255,0.10)",
  },
  text: {
    primary: "#F0F2F7",
    secondary: "#9BA3B8",
    muted: "#5A6278",
  },
  /** Per-metric accent palettes (from, via, to for gradients) */
  readiness: {
    from: "#00D2FF",
    via: "#0099CC",
    to: "#006699",
    glow: "rgba(0,210,255,0.18)",
    muted: "rgba(0,210,255,0.08)",
    solid: "#00D2FF",
  },
  sleep: {
    from: "#818CF8",
    via: "#6366F1",
    to: "#4338CA",
    glow: "rgba(129,140,248,0.18)",
    muted: "rgba(129,140,248,0.08)",
    solid: "#818CF8",
  },
  activity: {
    from: "#FB923C",
    via: "#F97316",
    to: "#EA580C",
    glow: "rgba(249,115,22,0.18)",
    muted: "rgba(249,115,22,0.08)",
    solid: "#FB923C",
  },
} as const;

export const radius = {
  card: "20px",
  pill: "9999px",
  sm: "8px",
  md: "12px",
} as const;

export const motion = {
  ring: "1.2s cubic-bezier(0.4, 0, 0.2, 1)",
  fade: "0.3s ease",
  count: "1s ease-out",
} as const;

export type Metric = "readiness" | "sleep" | "activity";

export const metricLabel: Record<Metric, string> = {
  readiness: "Readiness",
  sleep: "Sleep",
  activity: "Activity",
};
