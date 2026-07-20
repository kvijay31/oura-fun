const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

// F10.1 contract: POST /api/refresh kicks off an async incremental sync.
// status "started" | "running" → sync in progress (poll again)
// status "throttled"           → skipped, last_refreshed has timestamps
// status "done"                → sync just completed, last_refreshed has timestamps
export interface RefreshStatus {
  status: "started" | "running" | "throttled" | "done" | "error";
  last_refreshed: Record<string, string | null>;
  message?: string;
}

export async function triggerRefresh(person?: string): Promise<RefreshStatus> {
  const url = person ? `/api/refresh/${person}` : "/api/refresh";
  const res = await fetch(`${BASE}${url}`, { method: "POST", cache: "no-store" });
  if (!res.ok) {
    const body: { detail?: string } = await res.json().catch(() => ({}));
    return { status: "error", last_refreshed: {}, message: body.detail ?? `HTTP ${res.status}` };
  }
  return res.json() as Promise<RefreshStatus>;
}

export interface SleepRecord {
  day: string;
  score: number | null;
  total_sleep_duration: number | null;
  rem_sleep_duration: number | null;
  deep_sleep_duration: number | null;
  light_sleep_duration: number | null;
  efficiency: number | null;
  restless_periods: number | null;
  average_hrv: number | null;
  average_heart_rate: number | null;
}

export interface ReadinessRecord {
  day: string;
  score: number | null;
  temperature_deviation: number | null;
  hrv_balance_score: number | null;
  recovery_index_score: number | null;
  resting_heart_rate_score: number | null;
  sleep_balance_score: number | null;
}

export interface ActivityRecord {
  day: string;
  score: number | null;
  active_calories: number | null;
  total_calories: number | null;
  steps: number | null;
  equivalent_walking_minutes: number | null;
  high_activity_time: number | null;
  medium_activity_time: number | null;
  low_activity_time: number | null;
}

export async function fetchPeople(): Promise<string[]> {
  const data = await get<{ people: string[] }>("/api/people");
  return data.people;
}

export async function fetchSleep(person: string, start?: string, end?: string): Promise<SleepRecord[]> {
  const q = new URLSearchParams();
  if (start) q.set("start", start);
  if (end) q.set("end", end);
  const qs = q.toString();
  const data = await get<{ records: SleepRecord[] }>(`/api/sleep/${person}${qs ? `?${qs}` : ""}`);
  return data.records;
}

export async function fetchReadiness(person: string, start?: string, end?: string): Promise<ReadinessRecord[]> {
  const q = new URLSearchParams();
  if (start) q.set("start", start);
  if (end) q.set("end", end);
  const qs = q.toString();
  const data = await get<{ records: ReadinessRecord[] }>(`/api/readiness/${person}${qs ? `?${qs}` : ""}`);
  return data.records;
}

export async function fetchActivity(person: string, start?: string, end?: string): Promise<ActivityRecord[]> {
  const q = new URLSearchParams();
  if (start) q.set("start", start);
  if (end) q.set("end", end);
  const qs = q.toString();
  const data = await get<{ records: ActivityRecord[] }>(`/api/activity/${person}${qs ? `?${qs}` : ""}`);
  return data.records;
}

export async function fetchCompare(metric: string, start?: string, end?: string): Promise<Record<string, unknown[]>> {
  const q = new URLSearchParams({ metric });
  if (start) q.set("start", start);
  if (end) q.set("end", end);
  const data = await get<{ people: Record<string, unknown[]> }>(`/api/compare?${q.toString()}`);
  return data.people;
}

export function fmtMin(seconds: number | null): string {
  if (seconds == null) return "–";
  const m = Math.round(seconds / 60);
  const h = Math.floor(m / 60);
  const min = m % 60;
  return h > 0 ? `${h}h ${min}m` : `${min}m`;
}
