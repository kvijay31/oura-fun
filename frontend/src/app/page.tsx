"use client";

import { useState, useEffect, useRef } from "react";
import DashboardLayout from "@/components/DashboardLayout";
import RingScore from "@/components/RingScore";
import Card from "@/components/Card";
import TrendChart from "@/components/TrendChart";
import { fetchSleep, fetchReadiness, fetchActivity, type SleepRecord, type ReadinessRecord, type ActivityRecord } from "@/lib/api";
import { useRefresh } from "@/lib/refresh-context";

function OverviewContent({ person }: { person: string }) {
  const [sleep, setSleep] = useState<SleepRecord[]>([]);
  const [readiness, setReadiness] = useState<ReadinessRecord[]>([]);
  const [activity, setActivity] = useState<ActivityRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const { dataVersion } = useRefresh();
  const initialLoad = useRef(true);

  useEffect(() => {
    // Only show loading spinner on initial load — silent reload on refresh
    if (initialLoad.current) setLoading(true);
    Promise.all([
      fetchSleep(person),
      fetchReadiness(person),
      fetchActivity(person),
    ]).then(([s, r, a]) => {
      setSleep(s);
      setReadiness(r);
      setActivity(a);
      setLoading(false);
      initialLoad.current = false;
    }).catch(() => setLoading(false));
  }, [person, dataVersion]);

  const latestSleep = sleep.at(-1);
  const latestReadiness = readiness.at(-1);
  const latestActivity = activity.at(-1);

  const sleepTrend = sleep.map(d => ({ day: d.day, value: d.score }));
  const readinessTrend = readiness.map(d => ({ day: d.day, value: d.score }));
  const activityTrend = activity.map(d => ({ day: d.day, value: d.score }));

  if (loading) {
    return <div style={{ color: "var(--text-muted)", fontSize: 14 }}>Loading…</div>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 16 }}>
        <Card glow="rgba(0,210,255,0.10)">
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <RingScore score={latestReadiness?.score ?? null} metric="readiness" size={140} label="Readiness" />
            <TrendChart data={readinessTrend} color="#00D2FF" gradientId="ov-readiness" domain={[0, 100]} height={100} />
          </div>
        </Card>

        <Card glow="rgba(129,140,248,0.10)">
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <RingScore score={latestSleep?.score ?? null} metric="sleep" size={140} label="Sleep" />
            <TrendChart data={sleepTrend} color="#818CF8" gradientId="ov-sleep" domain={[0, 100]} height={100} />
          </div>
        </Card>

        <Card glow="rgba(249,115,22,0.10)">
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <RingScore score={latestActivity?.score ?? null} metric="activity" size={140} label="Activity" />
            <TrendChart data={activityTrend} color="#FB923C" gradientId="ov-activity" domain={[0, 100]} height={100} />
          </div>
        </Card>
      </div>

      {latestReadiness && (
        <p style={{ color: "var(--text-muted)", fontSize: 12, margin: 0 }}>
          Latest: {latestReadiness.day}
        </p>
      )}
    </div>
  );
}

export default function OverviewPage() {
  return (
    <DashboardLayout title="Overview">
      {(person) => <OverviewContent person={person} />}
    </DashboardLayout>
  );
}
