"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import RefreshBadge from "./RefreshBadge";

const links = [
  { href: "/", label: "Overview" },
  { href: "/sleep", label: "Sleep" },
  { href: "/readiness", label: "Readiness" },
  { href: "/activity", label: "Activity" },
  { href: "/compare", label: "Compare" },
  { href: "/chat", label: "Chat" },
];

export default function NavShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          background: "rgba(11,13,18,0.85)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--border-subtle)",
          position: "sticky",
          top: 0,
          zIndex: 50,
        }}
      >
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "0 24px", display: "flex", alignItems: "center", gap: 32, height: 56 }}>
          <span style={{ fontWeight: 700, fontSize: 16, letterSpacing: "-0.02em", color: "var(--text-primary)" }}>
            Oura
          </span>
          <nav style={{ display: "flex", gap: 4, flex: 1 }}>
            {links.map(({ href, label }) => {
              const active = pathname === href;
              return (
                <Link
                  key={href}
                  href={href}
                  style={{
                    padding: "6px 14px",
                    borderRadius: 8,
                    fontSize: 14,
                    fontWeight: active ? 600 : 400,
                    color: active ? "var(--text-primary)" : "var(--text-secondary)",
                    background: active ? "var(--bg-overlay)" : "transparent",
                    textDecoration: "none",
                    transition: "background 0.2s, color 0.2s",
                  }}
                >
                  {label}
                </Link>
              );
            })}
          </nav>
          <RefreshBadge />
        </div>
      </header>
      <main style={{ flex: 1, maxWidth: 1200, margin: "0 auto", width: "100%", padding: "32px 24px" }}>
        {children}
      </main>
    </div>
  );
}
