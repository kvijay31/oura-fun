// Design tokens — single source of truth for the Oura Fun design system.
// All components pull from here; never hardcode color/spacing/radius/motion values.
//
// CSS custom properties are defined in app/globals.css and mirror these values
// so they can be used in arbitrary CSS as well as in Tailwind class names.

export const colors = {
  bg: {
    base: "#0B0D12",      // page background
    surface: "#131720",   // card / panel background
    elevated: "#1C2333",  // elevated card (hover state, dropdowns)
    overlay: "#242D40",   // modal scrim / tooltip
  },
  text: {
    primary: "#F8FAFC",
    secondary: "#94A3B8",
    muted: "#475569",
  },
  accent: {
    readiness: "#22D3EE",  // cool teal/cyan  — readiness score, ring, chart line
    sleep: "#6366F1",      // soft indigo/blue — sleep score, ring, chart line
    activity: "#F97316",   // warm coral/orange — activity score, ring, chart line
    chat: "#A78BFA",       // violet — chat interface, AI assistant
  },
  accentDim: {
    readiness: "rgba(34, 211, 238, 0.15)",
    sleep: "rgba(99, 102, 241, 0.15)",
    activity: "rgba(249, 115, 22, 0.15)",
    chat: "rgba(167, 139, 250, 0.15)",
  },
  border: {
    default: "rgba(255, 255, 255, 0.06)",
    hover: "rgba(255, 255, 255, 0.12)",
    focus: "rgba(255, 255, 255, 0.20)",
  },
} as const;

export const spacing = {
  xs: "4px",
  sm: "8px",
  md: "16px",
  lg: "24px",
  xl: "32px",
  "2xl": "48px",
  "3xl": "64px",
} as const;

export const radii = {
  sm: "8px",
  md: "12px",
  lg: "16px",
  xl: "20px",
  "2xl": "24px",
  full: "9999px",
} as const;

export const shadows = {
  card: "0 0 0 1px rgba(255,255,255,0.06), 0 4px 24px rgba(0,0,0,0.4)",
  glow: {
    readiness: "0 0 40px rgba(34, 211, 238, 0.12)",
    sleep: "0 0 40px rgba(99, 102, 241, 0.12)",
    activity: "0 0 40px rgba(249, 115, 22, 0.12)",
    chat: "0 0 40px rgba(167, 139, 250, 0.12)",
  },
} as const;

export const motion = {
  duration: {
    fast: "150ms",
    base: "250ms",
    slow: "400ms",
  },
  easing: {
    smooth: "cubic-bezier(0.4, 0, 0.2, 1)",
    spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
  },
} as const;

// Per-metric design bundle — convenient when passing metric-specific styling
export type Metric = "readiness" | "sleep" | "activity";

export const metricTokens: Record<
  Metric,
  { accent: string; dim: string; glow: string; label: string }
> = {
  readiness: {
    accent: colors.accent.readiness,
    dim: colors.accentDim.readiness,
    glow: shadows.glow.readiness,
    label: "Readiness",
  },
  sleep: {
    accent: colors.accent.sleep,
    dim: colors.accentDim.sleep,
    glow: shadows.glow.sleep,
    label: "Sleep",
  },
  activity: {
    accent: colors.accent.activity,
    dim: colors.accentDim.activity,
    glow: shadows.glow.activity,
    label: "Activity",
  },
};
