"use client";

import { useState, useEffect, useRef } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import RingScore from "@/components/RingScore";
import Card from "@/components/Card";
import StatTile from "@/components/StatTile";
import TrendChart from "@/components/TrendChart";
import { fetchReadiness, type ReadinessRecord } from "@/lib/api";
import { useRefresh } from "@/lib/refresh-context";

const ACCENT = "#00D2FF";
const GLOW = "rgba(0,210,255,0.12)";

function ReadinessContent({ person }: { person: string }) {
  const [records, setRecords] = useState<ReadinessRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const { dataVersion } = useRefresh();
  const initialLoad = useRef(true);

  useEffect(() => {
    if (initialLoad.current) setLoading(true);
    fetchReadiness(person).then(r => {
      setRecords(r);
      setLoading(false);
      initialLoad.current = false;
    }).catch(() => setLoading(false));
  }, [person, dataVersion]);

  const latest = records.at(-1);
  const scoreTrend = records.map(d => ({ day: d.day, value: d.score }));
  const hrvTrend = records.map(d => ({ day: d.day, value: d.hrv_balance_score }));

  if (loading) return <div style={{ color: "var(--text-muted)", fontSize: 14 }}>Loading…</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <Card glow={GLOW}>
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 32, alignItems: "center" }}>
          <RingScore score={latest?.score ?? null} metric="readiness" size={160} label="Readiness Score" />
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <TrendChart data={scoreTrend} color={ACCENT} gradientId="rd-score" domain={[0, 100]} height={130} />
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 12 }}>
              {latest?.day ?? "No data"} — last 30 days
            </p>
          </div>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 10 }}>
        <StatTile label="HRV Balance" value={latest?.hrv_balance_score ?? null} accent={ACCENT} />
        <StatTile label="Recovery Index" value={latest?.recovery_index_score ?? null} accent={ACCENT} />
        <StatTile label="Resting HR" value={latest?.resting_heart_rate_score ?? null} />
        <StatTile label="Sleep Balance" value={latest?.sleep_balance_score ?? null} />
        <StatTile label="Temp Deviation" value={latest?.temperature_deviation != null ? latest.temperature_deviation.toFixed(2) : null} unit="°C" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <p style={{ margin: "0 0 12px", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600 }}>HRV Balance Score</p>
          <TrendChart data={hrvTrend} color={ACCENT} gradientId="rd-hrv" domain={[0, 100]} height={140} />
        </Card>
        <Card>
          <p style={{ margin: "0 0 12px", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600 }}>Recovery Score</p>
          <TrendChart
            data={records.map(d => ({ day: d.day, value: d.recovery_index_score }))}
            color={ACCENT}
            gradientId="rd-recovery"
            domain={[0, 100]}
            height={140}
          />
        </Card>
      </div>
    </div>
  );
}

export default function ReadinessPage() {
  return (
    <DashboardLayout title="Readiness">
      {(person) => <ReadinessContent person={person} />}
    </DashboardLayout>
  );
}
