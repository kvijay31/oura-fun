"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

const PERSON_COLORS = ["#00D2FF", "#818CF8", "#FB923C", "#34D399", "#F472B6"];

function formatDay(day: string) {
  const d = new Date(day + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

interface Props {
  people: string[];
  data: Record<string, Array<{ day: string; score: number | null }>>;
}

export default function MultiLineTrend({ people, data }: Props) {
  const daySet = new Set<string>();
  for (const records of Object.values(data)) {
    for (const r of records) daySet.add(r.day);
  }
  const days = Array.from(daySet).sort();

  const chartData = days.map(day => {
    const point: Record<string, string | number | null> = { day };
    for (const p of people) {
      const rec = data[p]?.find(r => r.day === day);
      point[p] = rec?.score ?? null;
    }
    return point;
  });

  if (chartData.length === 0) {
    return <div style={{ color: "var(--text-muted)", fontSize: 13 }}>No data</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={chartData} margin={{ top: 6, right: 4, left: -24, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="rgba(255,255,255,0.04)" />
        <XAxis
          dataKey="day"
          tickFormatter={formatDay}
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
        />
        <YAxis domain={[0, 100]} tick={{ fill: "var(--text-muted)", fontSize: 11 }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{
            background: "var(--bg-overlay)",
            border: "1px solid var(--border-muted)",
            borderRadius: 10,
            color: "var(--text-primary)",
            fontSize: 12,
          }}
          labelFormatter={(label: unknown) => formatDay(String(label))}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--text-secondary)", textTransform: "capitalize" }} />
        {people.map((p, i) => (
          <Line
            key={p}
            type="monotone"
            dataKey={p}
            stroke={PERSON_COLORS[i % PERSON_COLORS.length]}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
            connectNulls={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
