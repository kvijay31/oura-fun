interface StatTileProps {
  label: string;
  value: string | number | null;
  unit?: string;
  accent?: string;
}

export default function StatTile({ label, value, unit, accent }: StatTileProps) {
  return (
    <div
      style={{
        background: "var(--bg-elevated)",
        borderRadius: 14,
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      <span style={{ color: "var(--text-muted)", fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
        {label}
      </span>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
        <span style={{ color: accent || "var(--text-primary)", fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}>
          {value ?? "–"}
        </span>
        {unit && (
          <span style={{ color: "var(--text-muted)", fontSize: 12, fontWeight: 500 }}>{unit}</span>
        )}
      </div>
    </div>
  );
}
