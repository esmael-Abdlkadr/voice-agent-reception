"use client";

import { useCallback, useEffect, useState } from "react";
import { Mic, Plus } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { TestCallPanel } from "@/components/test-call-panel";
import { api } from "@/lib/api";
import type { Agent } from "@/lib/types";

export default function CallPage() {
  return (
    <AppShell requires="viewer">
      <CallConsole />
    </AppShell>
  );
}

function CallConsole() {
  const { currentWorkspaceId, workspaces, openNewWorkspaceModal } = useAuth();
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (currentWorkspaceId === null) {
      setAgents(null);
      return;
    }
    setError(null);
    try {
      const list = await api.listAgents(currentWorkspaceId);
      const active = list.filter((a) => a.is_active);
      setAgents(active);
      setSelectedId((prev) => {
        if (prev !== null && active.some((a) => a.id === prev)) return prev;
        return active[0]?.id ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [currentWorkspaceId]);

  useEffect(() => {
    reload();
  }, [reload]);

  if (currentWorkspaceId === null) {
    return (
      <EmptyShell
        title={workspaces.length === 0 ? "No workspaces yet" : "No workspace selected"}
        body={
          workspaces.length === 0
            ? "Ask an administrator to add you to a workspace, then you can place a call."
            : "Pick a workspace from the sidebar to place a call."
        }
        cta={
          workspaces.length === 0 ? (
            <button
              type="button"
              onClick={openNewWorkspaceModal}
              className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-accent-400 px-3.5 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300"
            >
              <Plus className="h-4 w-4" />
              Create workspace
            </button>
          ) : null
        }
      />
    );
  }

  if (agents === null) {
    return <EmptyShell title="Loading agents..." body="" />;
  }

  const selected = agents.find((a) => a.id === selectedId) ?? null;

  return (
    <div className="mx-auto max-w-3xl px-10 pb-16 pt-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
          Test call
        </h1>
        <p className="mt-1 text-sm text-zinc-400">
          Talk to the receptionist in your browser. Calls you place here show up
          in your own call history.
        </p>
      </header>

      {error && (
        <p className="mb-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      )}

      {agents.length === 0 ? (
        <EmptyShell
          title="No active agent"
          body="This workspace doesn't have an active agent yet. An administrator needs to configure one on the Agent page before you can place a call."
        />
      ) : (
        <div className="space-y-5">
          {agents.length > 1 && (
            <label className="block">
              <span className="block text-[11px] font-medium uppercase tracking-wider text-zinc-500">
                Agent
              </span>
              <select
                value={selectedId ?? ""}
                onChange={(e) => setSelectedId(Number(e.target.value))}
                className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-100 outline-none transition focus:border-accent-400/60 focus:shadow-glow"
              >
                {agents.map((a) => (
                  <option key={a.id} value={a.id} className="bg-zinc-900">
                    {a.name}
                  </option>
                ))}
              </select>
            </label>
          )}

          {selected && (
            <TestCallPanel
              workspaceId={currentWorkspaceId}
              agentId={selected.id}
              agentName={selected.name}
            />
          )}
        </div>
      )}
    </div>
  );
}

function EmptyShell({
  title,
  body,
  cta,
}: {
  title: string;
  body: string;
  cta?: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-3xl px-10 pb-16 pt-10">
      <div className="grid place-items-center rounded-2xl border border-zinc-800 bg-zinc-900/30 py-20 text-center">
        <Mic className="mb-3 h-6 w-6 text-zinc-600" />
        <h2 className="text-base font-medium text-zinc-200">{title}</h2>
        {body && <p className="mt-1 max-w-sm text-sm text-zinc-500">{body}</p>}
        {cta}
      </div>
    </div>
  );
}
