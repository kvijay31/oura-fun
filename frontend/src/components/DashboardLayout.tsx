"use client";

import { useState, useEffect } from "react";
import NavShell from "./NavShell";
import PersonPicker from "./PersonPicker";
import { fetchPeople } from "@/lib/api";

interface DashboardLayoutProps {
  children: (person: string) => React.ReactNode;
  title: string;
}

export default function DashboardLayout({ children, title }: DashboardLayoutProps) {
  const [people, setPeople] = useState<string[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPeople()
      .then(p => {
        setPeople(p);
        if (p.length > 0) setSelected(p[0]);
      })
      .catch(e => setError(String(e)));
  }, []);

  return (
    <NavShell>
      <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.03em", color: "var(--text-primary)", margin: 0 }}>
            {title}
          </h1>
          <PersonPicker people={people} selected={selected} onChange={setSelected} />
        </div>
        {error && (
          <div style={{ color: "#F87171", background: "rgba(248,113,113,0.08)", borderRadius: 12, padding: "12px 16px", fontSize: 13 }}>
            Could not reach API — make sure <code>uv run uvicorn src.oura_fun.api.app:app --port 8000</code> is running.
          </div>
        )}
        {!error && !selected && (
          <div style={{ color: "var(--text-muted)", fontSize: 14 }}>
            No data ingested yet — run the backfill script (F2.3) to populate the dashboard.
          </div>
        )}
        {selected && children(selected)}
      </div>
    </NavShell>
  );
}
