"use client";

import { useState, useEffect, useRef } from "react";
import NavShell from "@/components/NavShell";
import Card from "@/components/Card";
import { addPerson, fetchPeople, type AddPersonResult } from "@/lib/api";

type FormState =
  | { kind: "idle" }
  | { kind: "validating" }
  | { kind: "success"; result: AddPersonResult }
  | { kind: "error"; message: string };

function AddPersonForm({ onAdded }: { onAdded: () => void }) {
  const [name, setName] = useState("");
  const [token, setToken] = useState("");
  const [state, setState] = useState<FormState>({ kind: "idle" });
  const nameRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setState({ kind: "validating" });
    try {
      const result = await addPerson(name.trim().toLowerCase(), token.trim());
      setState({ kind: "success", result });
      setName("");
      setToken("");
      onAdded();
    } catch (err) {
      setState({ kind: "error", message: err instanceof Error ? err.message : String(err) });
    }
  }

  function reset() {
    setState({ kind: "idle" });
    nameRef.current?.focus();
  }

  const isValidating = state.kind === "validating";

  return (
    <Card style={{ maxWidth: 480 }}>
      <h2 style={{ margin: "0 0 6px", fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
        Add person
      </h2>
      <p style={{ margin: "0 0 24px", fontSize: 13, color: "var(--text-muted)", lineHeight: 1.5 }}>
        Generate a personal access token at{" "}
        <span style={{ color: "var(--c-readiness)", fontFamily: "monospace", fontSize: 12 }}>
          cloud.ouraring.com/personal-access-tokens
        </span>
        . The token is validated live before saving.
      </p>

      {state.kind === "success" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 12,
              background: "rgba(0,210,255,0.06)",
              border: "1px solid rgba(0,210,255,0.18)",
              borderRadius: 12,
              padding: "14px 16px",
            }}
          >
            <span style={{ fontSize: 18, lineHeight: 1 }}>✓</span>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: "var(--c-readiness)" }}>
                {state.result.person_id} added
              </span>
              {state.result.email && (
                <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                  Oura account: {state.result.email}
                </span>
              )}
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                Initial backfill started — data will appear within a few minutes.
              </span>
            </div>
          </div>
          <button
            onClick={reset}
            style={{
              alignSelf: "flex-start",
              background: "var(--bg-overlay)",
              color: "var(--text-secondary)",
              border: "1px solid var(--border-muted)",
              borderRadius: 10,
              padding: "8px 16px",
              fontSize: 13,
              cursor: "pointer",
              transition: "background 0.15s",
            }}
          >
            Add another
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Name
            </span>
            <input
              ref={nameRef}
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. alice"
              required
              disabled={isValidating}
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-muted)",
                borderRadius: 10,
                color: "var(--text-primary)",
                fontSize: 14,
                padding: "10px 14px",
                outline: "none",
                transition: "border-color 0.15s",
                fontFamily: "inherit",
                opacity: isValidating ? 0.5 : 1,
              }}
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-secondary)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
              Oura personal access token
            </span>
            <input
              type="password"
              value={token}
              onChange={e => setToken(e.target.value)}
              placeholder="Paste your token here"
              required
              disabled={isValidating}
              style={{
                background: "var(--bg-elevated)",
                border: "1px solid var(--border-muted)",
                borderRadius: 10,
                color: "var(--text-primary)",
                fontSize: 14,
                padding: "10px 14px",
                outline: "none",
                transition: "border-color 0.15s",
                fontFamily: "monospace",
                opacity: isValidating ? 0.5 : 1,
              }}
            />
          </label>

          {state.kind === "error" && (
            <div
              style={{
                background: "rgba(248,113,113,0.08)",
                border: "1px solid rgba(248,113,113,0.25)",
                borderRadius: 10,
                padding: "10px 14px",
                fontSize: 13,
                color: "#F87171",
              }}
            >
              {state.message}
            </div>
          )}

          <button
            type="submit"
            disabled={isValidating || !name.trim() || !token.trim()}
            style={{
              background: isValidating
                ? "var(--bg-overlay)"
                : "linear-gradient(135deg, var(--c-readiness-from), var(--c-readiness-to))",
              color: isValidating ? "var(--text-muted)" : "#0B0D12",
              border: "none",
              borderRadius: 10,
              padding: "11px 20px",
              fontSize: 14,
              fontWeight: 600,
              cursor: isValidating ? "default" : "pointer",
              transition: "opacity 0.15s",
              opacity: (!name.trim() || !token.trim()) ? 0.4 : 1,
              fontFamily: "inherit",
            }}
          >
            {isValidating ? "Validating token…" : "Add person"}
          </button>
        </form>
      )}
    </Card>
  );
}

function PeopleList({ refreshKey }: { refreshKey: number }) {
  const [people, setPeople] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchPeople()
      .then(p => { setPeople(p); setLoading(false); })
      .catch(() => setLoading(false));
  }, [refreshKey]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "var(--text-primary)" }}>
        People
      </h2>
      {loading ? (
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Loading…</span>
      ) : people.length === 0 ? (
        <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
          No data ingested yet. Add a person above to get started.
        </span>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {people.map(p => (
            <div
              key={p}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: 12,
                padding: "12px 16px",
              }}
            >
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, var(--c-readiness-from), var(--c-readiness-to))",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 13,
                  fontWeight: 700,
                  color: "#0B0D12",
                  flexShrink: 0,
                }}
              >
                {p[0]?.toUpperCase() ?? "?"}
              </div>
              <span style={{ fontSize: 14, fontWeight: 500, color: "var(--text-primary)" }}>{p}</span>
              <span
                style={{
                  marginLeft: "auto",
                  fontSize: 11,
                  color: "var(--text-muted)",
                  background: "var(--bg-overlay)",
                  borderRadius: 6,
                  padding: "3px 8px",
                }}
              >
                active
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <NavShell>
      <div style={{ display: "flex", flexDirection: "column", gap: 36 }}>
        <div>
          <h1
            style={{
              fontSize: 26,
              fontWeight: 700,
              letterSpacing: "-0.03em",
              color: "var(--text-primary)",
              margin: "0 0 4px",
            }}
          >
            Settings
          </h1>
          <p style={{ margin: 0, fontSize: 14, color: "var(--text-muted)" }}>
            Manage people and their Oura tokens.
          </p>
        </div>

        <PeopleList refreshKey={refreshKey} />

        <AddPersonForm onAdded={() => setRefreshKey(k => k + 1)} />
      </div>
    </NavShell>
  );
}
