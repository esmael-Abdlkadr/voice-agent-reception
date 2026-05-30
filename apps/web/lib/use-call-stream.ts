"use client";

import { useEffect, useState } from "react";
import { API_BASE_URL, getStoredToken } from "@/lib/api";

export type StreamedTurn = {
  role: "user" | "agent";
  text: string;
  ts_ms: number;
};

export type StreamedTool = {
  tool_name: string;
  status: string;
  ts_ms: number;
  duration_ms: number;
};

type StreamState = {
  turns: StreamedTurn[];
  tools: StreamedTool[];
};

/**
 * Subscribes to the live SSE stream and collects `call_turn` / `call_tool`
 * events for one specific call. Only active when `enabled` is true (i.e. the
 * call is in progress) — completed calls read their transcript from the DB.
 *
 * Returns turns/tools that arrived *during this subscription*. The Calls
 * detail page merges these on top of whatever was already persisted, so a
 * mid-call refresh shows the DB-backed partial transcript and then resumes
 * streaming.
 */
export function useCallStream(
  workspaceId: number | null,
  callId: number | null,
  enabled: boolean
): StreamState {
  const [state, setState] = useState<StreamState>({ turns: [], tools: [] });

  useEffect(() => {
    setState({ turns: [], tools: [] });
    if (!enabled || workspaceId === null || callId === null) return;
    if (typeof window === "undefined") return;

    const token = getStoredToken();
    if (!token) return;

    const es = new EventSource(
      `${API_BASE_URL}/events?token=${encodeURIComponent(token)}`
    );

    es.onmessage = (e) => {
      let event: {
        type: string;
        workspace_id: number;
        call_id?: number;
        data: Record<string, unknown>;
      };
      try {
        event = JSON.parse(e.data);
      } catch {
        return;
      }
      if (event.workspace_id !== workspaceId || event.call_id !== callId) return;

      if (event.type === "call_turn") {
        const turn = event.data as unknown as StreamedTurn;
        setState((prev) => {
          if (
            prev.turns.some(
              (t) => t.ts_ms === turn.ts_ms && t.role === turn.role
            )
          ) {
            return prev;
          }
          return { ...prev, turns: [...prev.turns, turn] };
        });
      } else if (event.type === "call_tool") {
        const tool = event.data as unknown as StreamedTool;
        setState((prev) => ({ ...prev, tools: [...prev.tools, tool] }));
      }
    };

    return () => es.close();
  }, [workspaceId, callId, enabled]);

  return state;
}
