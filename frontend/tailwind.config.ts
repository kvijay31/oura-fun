import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Backgrounds
        bg: {
          base: "#0B0D12",
          surface: "#131720",
          elevated: "#1C2333",
          overlay: "#242D40",
        },
        // Text
        ink: {
          primary: "#F8FAFC",
          secondary: "#94A3B8",
          muted: "#475569",
        },
        // Per-metric accents
        readiness: {
          DEFAULT: "#22D3EE",
          dim: "rgba(34,211,238,0.15)",
        },
        sleep: {
          DEFAULT: "#6366F1",
          dim: "rgba(99,102,241,0.15)",
        },
        activity: {
          DEFAULT: "#F97316",
          dim: "rgba(249,115,22,0.15)",
        },
        chat: {
          DEFAULT: "#A78BFA",
          dim: "rgba(167,139,250,0.15)",
        },
        // Borders
        edge: {
          DEFAULT: "rgba(255,255,255,0.06)",
          hover: "rgba(255,255,255,0.12)",
          focus: "rgba(255,255,255,0.2)",
        },
      },
      borderRadius: {
        sm: "8px",
        md: "12px",
        lg: "16px",
        xl: "20px",
        "2xl": "24px",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Display",
          "SF Pro Text",
          "system-ui",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 0 0 1px rgba(255,255,255,0.06), 0 4px 24px rgba(0,0,0,0.4)",
        "glow-readiness": "0 0 40px rgba(34,211,238,0.12)",
        "glow-sleep": "0 0 40px rgba(99,102,241,0.12)",
        "glow-activity": "0 0 40px rgba(249,115,22,0.12)",
        "glow-chat": "0 0 40px rgba(167,139,250,0.12)",
      },
      transitionTimingFunction: {
        smooth: "cubic-bezier(0.4, 0, 0.2, 1)",
      },
      transitionDuration: {
        base: "250ms",
        slow: "400ms",
      },
      animation: {
        "fade-in": "fadeIn 300ms cubic-bezier(0.4, 0, 0.2, 1) forwards",
        "slide-up": "slideUp 300ms cubic-bezier(0.4, 0, 0.2, 1) forwards",
        "pulse-dot": "pulseDot 1.4s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pulseDot: {
          "0%, 80%, 100%": { transform: "scale(0.6)", opacity: "0.4" },
          "40%": { transform: "scale(1)", opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
