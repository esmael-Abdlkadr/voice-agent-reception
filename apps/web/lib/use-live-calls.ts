"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL, api, getStoredToken } from "@/lib/api";
import type { CallSummary } from "@/lib/types";

type LiveEvent = {
  type: "call";
  workspace_id: number;
  data: CallSummary;
};

/**
 * Live-updating list of calls for the given workspace.
 *
 *   - Fetches the initial list on mount / workspace change.
 *   - Opens an SSE stream to /events and merges incoming "call" events.
 *   - The SSE server sends a snapshot of every active call on connect,
 *     so reconnecting after a refresh gets you live state immediately.
 *
 * Returns the list newest-first; callers can filter to active vs not.
 */
export function useLiveCalls(workspaceId: number | null): CallSummary[] {
  const [calls, setCalls] = useState<CallSummary[]>([]);

  useEffect(() => {
    if (workspaceId === null) {
      setCalls([]);
      return;
    }
    let cancelled = false;
    api
      .listCalls(workspaceId)
      .then((list) => {
        if (!cancelled) setCalls(list);
      })
      .catch(() => {
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId]);

  useEffect(() => {
    if (workspaceId === null) return;
    if (typeof window === "undefined") return;

    const token = getStoredToken();
    if (!token) return;

    const url = `${API_BASE_URL}/events?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);

    es.onmessage = (e) => {
      let event: LiveEvent;
      try {
        event = JSON.parse(e.data);
      } catch {
        return;
      }
      if (event.type !== "call") return;
      if (event.workspace_id !== workspaceId) return;
      const incoming = event.data;
      setCalls((prev) => {
        const idx = prev.findIndex((c) => c.id === incoming.id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = incoming;
          return next;
        }
        const merged = [incoming, ...prev];
        merged.sort(
          (a, b) =>
            new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
        );
        return merged;
      });
    };

    es.onerror = () => {
    };

    return () => {
      es.close();
    };
  }, [workspaceId]);

  return calls;
}
