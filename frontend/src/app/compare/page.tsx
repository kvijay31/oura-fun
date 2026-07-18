"use client";

import { useState, useEffect } from "react";
import NavShell from "@/components/NavShell";
import RingScore from "@/components/RingScore";
import Card from "@/components/Card";
import MultiLineTrend from "@/components/MultiLineTrend";
import { fetchPeople, fetchSleep, fetchReadiness, fetchActivity } from "@/lib/api";
import type { SleepRecord, ReadinessRecord, ActivityRecord } from "@/lib/api";
import type { Metric } from "@/lib/tokens";

const METRIC_CONFIG: Record<Metric, { color: string; glow: string; label: string }> = {
  readiness: { color: "#00D2FF", glow: "rgba(0,210,255,0.12)", label: "Readiness" },
  sleep: { color: "#818CF8", glow: "rgba(129,140,248,0.12)", label: "Sleep" },
  activity: { color: "#FB923C", glow: "rgba(249,115,22,0.12)", label: "Activity" },
};

type MetricRecord = SleepRecord | ReadinessRecord | ActivityRecord;

async function fetchForMetric(metric: Metric, person: string): Promise<MetricRecord[]> {
  if (metric === "sleep") return fetchSleep(person);
  if (metric === "readiness") return fetchReadiness(person);
  return fetchActivity(person);
}

function CompareContent() {
  const [people, setPeople] = useState<string[]>([]);
  const [metric, setMetric] = useState<Metric>("readiness");
  const [data, setData] = useState<Record<string, MetricRecord[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPeople()
      .then(p => setPeople(p))
      .catch(e => setError(String(e)));
  }, []);

  useEffect(() => {
    if (people.length === 0) return;
    setLoading(true);
    Promise.all(people.map(p => fetchForMetric(metric, p).then(records => ({ person: p, records }))))
      .then(results => {
        const map: Record<string, MetricRecord[]> = {};
        for (const { person, records } of results) map[person] = records;
        setData(map);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [people, metric]);

  const cfg = METRIC_CONFIG[metric];

  const trendData: Record<string, Array<{ day: string; score: number | null }>> = {};
  for (const [person, records] of Object.entries(data)) {
    trendData[person] = records.map(r => ({ day: r.day, score: r.score ?? null }));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <h1 style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-0.03em", color: "var(--text-primary)", margin: 0 }}>
          Compare
        </h1>
        <div style={{ display: "flex", gap: 8 }}>
          {(["readiness", "sleep", "activity"] as Metric[]).map(m => (
            <button
              key={m}
              onClick={() => setMetric(m)}
              style={{
                padding: "6px 16px",
                borderRadius: 9999,
                fontSize: 13,
                fontWeight: metric === m ? 600 : 400,
                border: `1px solid ${metric === m ? METRIC_CONFIG[m].color : "var(--border-muted)"}`,
                background: metric === m
                  ? `rgba(${m === "readiness" ? "0,210,255" : m === "sleep" ? "129,140,248" : "249,115,22"},0.10)`
                  : "transparent",
                color: metric === m ? METRIC_CONFIG[m].color : "var(--text-secondary)",
                cursor: "pointer",
                transition: "all 0.2s",
                textTransform: "capitalize",
              }}
            >
              {METRIC_CONFIG[m].label}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div style={{ color: "#F87171", background: "rgba(248,113,113,0.08)", borderRadius: 12, padding: "12px 16px", fontSize: 13 }}>
          Could not reach API — make sure the backend is running on port 8000.
        </div>
      )}

      {!loading && people.length === 0 && !error && (
        <div style={{ color: "var(--text-muted)", fontSize: 14 }}>No people found.</div>
      )}

      {loading && <div style={{ color: "var(--text-muted)", fontSize: 14 }}>Loading…</div>}

      {!loading && people.length > 0 && (
        <>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            {people.map(p => (
              <Card key={p} glow={cfg.glow} style={{ flex: "1 1 200px", display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                <span style={{ color: "var(--text-muted)", fontSize: 11, fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                  {p}
                </span>
                <RingScore score={data[p]?.at(-1)?.score ?? null} metric={metric} size={120} label={cfg.label} />
              </Card>
            ))}
          </div>

          <Card>
            <p style={{ margin: "0 0 16px", color: "var(--text-secondary)", fontSize: 13, fontWeight: 600 }}>
              {cfg.label} Score — 30-day trend
            </p>
            <MultiLineTrend people={people} data={trendData} />
          </Card>
        </>
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <NavShell>
      <CompareContent />
    </NavShell>
  );
}
