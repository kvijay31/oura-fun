"use client";

import { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import { triggerRefresh, fetchRefreshStatus } from "./api";

export type RefreshState = "idle" | "refreshing" | "done" | "unavailable";

interface RefreshCtx {
  refreshState: RefreshState;
  lastRefreshed: Record<string, string | null>;
  dataVersion: number;
  trigger: () => void;
}

const Ctx = createContext<RefreshCtx>({
  refreshState: "idle",
  lastRefreshed: {},
  dataVersion: 0,
  trigger: () => {},
});

export function useRefresh() {
  return useContext(Ctx);
}

const POLL_MS = 10_000;

export function RefreshProvider({ children }: { children: React.ReactNode }) {
  const [refreshState, setRefreshState] = useState<RefreshState>("idle");
  const [lastRefreshed, setLastRefreshed] = useState<Record<string, string | null>>({});
  const [dataVersion, setDataVersion] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Poll GET /api/refresh/status once. Returns true once any_running is false,
  // having already surfaced the results and stopped the interval.
  const pollUntilDone = useCallback(async (): Promise<boolean> => {
    let status;
    try {
      status = await fetchRefreshStatus();
    } catch {
      // transient error — keep polling on the next tick
      return false;
    }
    if (!mountedRef.current) return true;
    if (!status.any_running) {
      stopPolling();
      const lastRefresh: Record<string, string | null> = {};
      for (const [pid, s] of Object.entries(status.refresh)) {
        lastRefresh[pid] = s.last_refresh;
      }
      setLastRefreshed(lastRefresh);
      setRefreshState("done");
      setDataVersion(v => v + 1);
      return true;
    }
    return false;
  }, [stopPolling]);

  const trigger = useCallback(async () => {
    if (refreshState === "refreshing") return;
    setRefreshState("refreshing");

    try {
      await triggerRefresh();
    } catch {
      if (mountedRef.current) setRefreshState("unavailable");
      return;
    }

    if (!mountedRef.current) return;

    // Kickoff returns immediately with per-person "started"/"throttled"/etc — the
    // actual completion is tracked by GET /api/refresh/status, so poll that
    // until it reports nothing running.
    const done = await pollUntilDone();
    if (!done) {
      stopPolling();
      pollRef.current = setInterval(pollUntilDone, POLL_MS);
    }
  }, [refreshState, pollUntilDone, stopPolling]);

  // Trigger once on mount. Deferred a tick so the initial setState inside
  // trigger() doesn't happen synchronously within the effect body.
  useEffect(() => {
    const id = setTimeout(trigger, 0);
    return () => clearTimeout(id);
    // intentionally omit trigger from deps to run only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Ctx.Provider value={{ refreshState, lastRefreshed, dataVersion, trigger }}>
      {children}
    </Ctx.Provider>
  );
}
