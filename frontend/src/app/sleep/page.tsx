"use client";

import { useState, useEffect } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import RingScore from "@/components/RingScore";
import Card from "@/components/Card";
import StatTile from "@/components/StatTile";
import TrendChart from "@/components/TrendChart";
import { fetchSleep, fmtMin, type SleepRecord } from "@/lib/api";

const ACCENT = "#818CF8";
const GLOW = "rgba(129,140,248,0.12)";

function SleepContent({ person }: { person: string }) {
  const [records, setRecords] = useState<SleepRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchSleep(person).then(r => { setRecords(r); setLoading(false); }).catch(() => setLoading(false));
  }, [person]);

  const latest = records.at(-1);
  const scoreTrend = records.map(d => ({ day: d.day, value: d.score }));
  const hrvTrend = records.map(d => ({ day: d.day, value: d.average_hrv }));
  const durationTrend = records.map(d => ({
    day: d.day,
    value: d.total_sleep_duration != null ? Math.round(d.total_sleep_duration / 3600 * 10) / 10 : null,
  }));

  if (loading) return <div style={{ color: "var(--text-muted)", fontSize: 14 }}>Loading…</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Hero */}
      <Card glow={GLOW}>
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 32, alignItems: "center" }}>
          <RingScore score={latest?.score ?? null} metric="sleep" size={160} label="Sleep Score" />
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <TrendChart data={scoreTrend} color={ACCENT} gradientId="sl-score" domain={[0, 100]} height={130} />
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 12 }}>
              {latest?.day ?? "No data"} — last 30 days
            </p>
          </div>
        </div>
      </Card>

      {/* Stat tiles */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 10 }}>
        <StatTile label="Total Sleep" value={fmtMin(latest?.total_sleep_duration ?? null)} accent={ACCENT} />
        <StatTile label="REM" value={fmtMin(latest?.rem_sleep_duration ?? null)} accent={ACCENT} />
        <StatTile label="Deep" value={fmtMin(latest?.deep_sleep_duration ?? null)} accent={ACCENT} />
        <StatTile label="Efficiency" value={latest?.efficiency != null ? `${latest.efficiency}%` : null} />
        <StatTile label="Avg HRV" value={latest?.average_hrv != null ? Math.round(latest.average_hrv) : null} unit="ms" />
        <StatTile label="Resting HR" value={latest?.average_heart_rate != null ? Math.round(latest.average_heart_rate) : null} unit="bpm" />
        <StatTile label="Restless" value={latest?.restless_periods ?? null} unit="periods" />
      </div>

      {/* Secondary charts */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <p style={{ margin: "0 0 12px", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600 }}>HRV Trend</p>
          <TrendChart data={hrvTrend} color={ACCENT} gradientId="sl-hrv" height={140} />
        </Card>
        <Card>
          <p style={{ margin: "0 0 12px", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600 }}>Duration (hours)</p>
          <TrendChart data={durationTrend} color={ACCENT} gradientId="sl-dur" height={140} />
        </Card>
      </div>
    </div>
  );
}

export default function SleepPage() {
  return (
    <DashboardLayout title="Sleep">
      {(person) => <SleepContent person={person} />}
    </DashboardLayout>
  );
}
