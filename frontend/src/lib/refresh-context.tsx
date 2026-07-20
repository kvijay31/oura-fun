"use client";

import { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import { triggerRefresh, type RefreshStatus } from "./api";

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

  const finishRefresh = useCallback((result: RefreshStatus) => {
    if (!mountedRef.current) return;
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setLastRefreshed(result.last_refreshed ?? {});
    setRefreshState("done");
    setDataVersion(v => v + 1);
  }, []);

  const trigger = useCallback(async () => {
    if (refreshState === "refreshing") return;
    setRefreshState("refreshing");

    let result: RefreshStatus;
    try {
      result = await triggerRefresh();
    } catch {
      if (mountedRef.current) setRefreshState("unavailable");
      return;
    }

    if (!mountedRef.current) return;

    if (result.status === "started" || result.status === "running") {
      // Async refresh — poll until completion
      pollRef.current = setInterval(async () => {
        try {
          const poll = await triggerRefresh();
          if (poll.status !== "started" && poll.status !== "running") {
            finishRefresh(poll);
          }
        } catch {
          // keep polling
        }
      }, POLL_MS);
    } else {
      finishRefresh(result);
    }
  }, [refreshState, finishRefresh]);

  // Trigger once on mount
  useEffect(() => {
    trigger();
    // intentionally omit trigger from deps to run only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Ctx.Provider value={{ refreshState, lastRefreshed, dataVersion, trigger }}>
      {children}
    </Ctx.Provider>
  );
}
