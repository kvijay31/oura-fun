"use client";

interface PersonPickerProps {
  people: string[];
  selected: string;
  onChange: (p: string) => void;
}

export default function PersonPicker({ people, selected, onChange }: PersonPickerProps) {
  if (people.length === 0) return null;
  return (
    <div style={{ display: "flex", gap: 8 }}>
      {people.map(p => {
        const active = p === selected;
        return (
          <button
            key={p}
            onClick={() => onChange(p)}
            style={{
              padding: "6px 16px",
              borderRadius: 9999,
              fontSize: 13,
              fontWeight: active ? 600 : 400,
              border: `1px solid ${active ? "var(--c-readiness)" : "var(--border-muted)"}`,
              background: active ? "rgba(0,210,255,0.10)" : "transparent",
              color: active ? "var(--c-readiness)" : "var(--text-secondary)",
              cursor: "pointer",
              transition: "all 0.2s",
              textTransform: "capitalize",
            }}
          >
            {p}
          </button>
        );
      })}
    </div>
  );
}
