import type { ReactNode, CSSProperties } from "react";

interface CardProps {
  children: ReactNode;
  glow?: string;
  className?: string;
  style?: CSSProperties;
}

export default function Card({ children, glow, className = "", style }: CardProps) {
  return (
    <div
      className={className}
      style={{
        background: "var(--bg-surface)",
        borderRadius: "var(--radius-card)",
        border: "1px solid var(--border-subtle)",
        padding: "24px",
        position: "relative",
        overflow: "hidden",
        ...(glow && { boxShadow: `0 0 40px ${glow}` }),
        ...style,
      }}
    >
      {children}
    </div>
  );
}
