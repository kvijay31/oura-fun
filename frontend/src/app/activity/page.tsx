"use client";

import { useState, useEffect } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import RingScore from "@/components/RingScore";
import Card from "@/components/Card";
import StatTile from "@/components/StatTile";
import TrendChart from "@/components/TrendChart";
import { fetchActivity, fmtMin, type ActivityRecord } from "@/lib/api";

const ACCENT = "#FB923C";
const GLOW = "rgba(249,115,22,0.12)";

function ActivityContent({ person }: { person: string }) {
  const [records, setRecords] = useState<ActivityRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchActivity(person).then(r => { setRecords(r); setLoading(false); }).catch(() => setLoading(false));
  }, [person]);

  const latest = records.at(-1);
  const scoreTrend = records.map(d => ({ day: d.day, value: d.score }));
  const stepsTrend = records.map(d => ({ day: d.day, value: d.steps }));
  const calTrend = records.map(d => ({ day: d.day, value: d.active_calories }));

  if (loading) return <div style={{ color: "var(--text-muted)", fontSize: 14 }}>Loading…</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <Card glow={GLOW}>
        <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 32, alignItems: "center" }}>
          <RingScore score={latest?.score ?? null} metric="activity" size={160} label="Activity Score" />
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <TrendChart data={scoreTrend} color={ACCENT} gradientId="ac-score" domain={[0, 100]} height={130} />
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: 12 }}>
              {latest?.day ?? "No data"} — last 30 days
            </p>
          </div>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 10 }}>
        <StatTile label="Steps" value={latest?.steps?.toLocaleString() ?? null} accent={ACCENT} />
        <StatTile label="Active Cal" value={latest?.active_calories ?? null} unit="kcal" accent={ACCENT} />
        <StatTile label="Total Cal" value={latest?.total_calories ?? null} unit="kcal" />
        <StatTile label="High Activity" value={fmtMin(latest?.high_activity_time != null ? latest.high_activity_time * 60 : null)} />
        <StatTile label="Walking" value={latest?.equivalent_walking_minutes ?? null} unit="min" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <p style={{ margin: "0 0 12px", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600 }}>Steps Trend</p>
          <TrendChart data={stepsTrend} color={ACCENT} gradientId="ac-steps" height={140} />
        </Card>
        <Card>
          <p style={{ margin: "0 0 12px", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600 }}>Active Calories</p>
          <TrendChart data={calTrend} color={ACCENT} gradientId="ac-cal" height={140} />
        </Card>
      </div>
    </div>
  );
}

export default function ActivityPage() {
  return (
    <DashboardLayout title="Activity">
      {(person) => <ActivityContent person={person} />}
    </DashboardLayout>
  );
}
