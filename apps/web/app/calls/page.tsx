"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  Clock,
  Loader2,
  PhoneCall,
  PhoneOff,
  Plus,
  User,
  Wrench,
} from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";
import type {
  CallDetail,
  CallStatus,
  CallSummary,
  CallToolCall,
  CallTurn,
} from "@/lib/types";

type StatusFilter = "all" | CallStatus;

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "completed", label: "Completed" },
  { value: "active", label: "Active" },
  { value: "escalated", label: "Escalated" },
  { value: "failed", label: "Failed" },
];

export default function CallsPage() {
  return (
    <AppShell>
      <Suspense fallback={null}>
        <CallsView />
      </Suspense>
    </AppShell>
  );
}

function CallsView() {
  const { currentWorkspaceId, workspaces, openNewWorkspaceModal } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const callIdParam = searchParams.get("call");
  const initialCallId = callIdParam ? Number(callIdParam) : null;

  const [calls, setCalls] = useState<CallSummary[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(initialCallId);
  const [detail, setDetail] = useState<CallDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [error, setError] = useState<string | null>(null);

  // Keep selected id in sync with the URL when the user navigates back/forward.
  useEffect(() => {
    const fromUrl = callIdParam ? Number(callIdParam) : null;
    if (fromUrl !== selectedId) {
      setSelectedId(fromUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [callIdParam]);

  // Push selected id into the URL so calls are linkable + back-button-able.
  function selectCall(id: number) {
    setSelectedId(id);
    const sp = new URLSearchParams(Array.from(searchParams.entries()));
    sp.set("call", String(id));
    router.replace(`/calls?${sp.toString()}`, { scroll: false });
  }

  const reload = useCallback(async () => {
    if (currentWorkspaceId === null) {
      setCalls(null);
      return;
    }
    try {
      const list = await api.listCalls(currentWorkspaceId);
      setCalls(list);
      // If the URL-supplied id is still valid, keep it; else fall back to first.
      setSelectedId((prev) => {
        if (prev !== null && list.some((c) => c.id === prev)) return prev;
        return list[0]?.id ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [currentWorkspaceId]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (currentWorkspaceId === null) return;
    const handle = window.setInterval(reload, 10_000);
    return () => window.clearInterval(handle);
  }, [reload, currentWorkspaceId]);

  useEffect(() => {
    if (selectedId === null || currentWorkspaceId === null) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    api
      .getCall(currentWorkspaceId, selectedId)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setDetailLoading(false));
  }, [selectedId, currentWorkspaceId]);

  const filtered = useMemo(() => {
    if (!calls) return [];
    if (statusFilter === "all") return calls;
    return calls.filter((c) => c.status === statusFilter);
  }, [calls, statusFilter]);

  if (currentWorkspaceId === null) {
    return (
      <EmptyShell
        title={workspaces.length === 0 ? "No workspaces yet" : "No workspace selected"}
        body={
          workspaces.length === 0
            ? "Create your first workspace before reviewing calls."
            : "Pick a workspace from the sidebar to see its calls."
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

  return (
    <div className="flex h-screen flex-col">
      <header className="border-b border-zinc-800/80 bg-zinc-950 px-10 py-6">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
              Calls
            </h1>
            <p className="mt-1 text-sm text-zinc-400">
              Every call this workspace has handled. Click a row for the
              transcript and tool calls.
            </p>
          </div>
          <div className="flex items-center gap-1 rounded-lg border border-zinc-800 bg-zinc-900/60 p-0.5">
            {STATUS_FILTERS.map((f) => {
              const active = statusFilter === f.value;
              return (
                <button
                  key={f.value}
                  type="button"
                  onClick={() => setStatusFilter(f.value)}
                  className={`rounded-md px-2.5 py-1 text-xs transition ${
                    active
                      ? "bg-zinc-100 text-zinc-900"
                      : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
                  }`}
                >
                  {f.label}
                </button>
              );
            })}
          </div>
        </div>
        {error && (
          <p className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
            {error}
          </p>
        )}
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="w-[380px] shrink-0 overflow-y-auto border-r border-zinc-800/80 bg-zinc-950">
          {calls === null ? (
            <p className="px-5 py-4 text-sm text-zinc-500">Loading...</p>
          ) : filtered.length === 0 ? (
            <div className="grid place-items-center px-6 py-20 text-center">
              <PhoneCall className="mb-2 h-5 w-5 text-zinc-600" />
              <p className="text-sm font-medium text-zinc-200">
                {calls.length === 0 ? "No calls yet" : "No calls match this filter"}
              </p>
              <p className="mt-1 max-w-[260px] text-xs text-zinc-500">
                {calls.length === 0
                  ? "Calls show up here once a caller talks to the agent. Try one yourself from Agent."
                  : "Try All to see everything in this workspace."}
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-zinc-800/60">
              {filtered.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => selectCall(c.id)}
                    className={`flex w-full flex-col gap-1 px-5 py-3.5 text-left transition ${
                      selectedId === c.id
                        ? "bg-zinc-900"
                        : "hover:bg-zinc-900/50"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2">
                        <StatusDot status={c.status} />
                        <span className="truncate text-sm text-zinc-100">
                          {c.caller_identity}
                        </span>
                      </div>
                      <span className="shrink-0 text-[11px] tabular-nums text-zinc-500">
                        {formatRelative(c.started_at)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-zinc-500">
                      <span className="truncate font-mono">{c.livekit_room_id}</span>
                      <span>·</span>
                      <span className="tabular-nums">{formatDuration(c.duration_ms)}</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>

        <section className="min-w-0 flex-1 overflow-y-auto bg-zinc-950">
          {selectedId === null ? (
            <EmptyState
              icon={<PhoneCall className="h-5 w-5" />}
              title="Pick a call"
              body="Select a call on the left to read its transcript."
            />
          ) : detailLoading || detail === null ? (
            <div className="grid place-items-center py-16 text-sm text-zinc-500">
              <Loader2 className="mb-2 h-5 w-5 animate-spin" />
              Loading call...
            </div>
          ) : (
            <CallDetailPanel call={detail} />
          )}
        </section>
      </div>
    </div>
  );
}

function CallDetailPanel({ call }: { call: CallDetail }) {
  return (
    <div className="grid gap-8 px-10 py-8 lg:grid-cols-[1fr_280px]">
      <article className="space-y-7">
        <header className="flex flex-wrap items-center gap-2">
          <StatusBadge status={call.status} />
          <h2 className="text-xl font-semibold tracking-tight text-zinc-100">
            {call.caller_identity}
          </h2>
          <span className="text-xs text-zinc-500">
            · {formatRelative(call.started_at)}
          </span>
        </header>

        {call.tool_calls.length > 0 && (
          <section>
            <h3 className="mb-2 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
              Tool calls · {call.tool_calls.length}
            </h3>
            <ul className="space-y-2">
              {call.tool_calls.map((tc) => (
                <ToolCallRow key={tc.id} tc={tc} />
              ))}
            </ul>
          </section>
        )}

        <section>
          <h3 className="mb-3 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
            Transcript · {call.turns.length}{" "}
            {call.turns.length === 1 ? "turn" : "turns"}
          </h3>
          {call.turns.length === 0 ? (
            <p className="rounded-xl border border-dashed border-zinc-800 px-4 py-10 text-center text-sm text-zinc-500">
              No transcript captured. The caller may have hung up before
              speaking.
            </p>
          ) : (
            <ol className="space-y-3">
              {call.turns.map((turn) => (
                <TranscriptBubble key={turn.id} turn={turn} />
              ))}
            </ol>
          )}
        </section>
      </article>

      <aside className="space-y-2.5 text-sm">
        <MetaRow icon={<Clock className="h-3.5 w-3.5" />} label="Duration">
          <span className="tabular-nums">{formatDuration(call.duration_ms)}</span>
        </MetaRow>
        <MetaRow icon={<PhoneCall className="h-3.5 w-3.5" />} label="Started">
          {new Date(call.started_at).toLocaleString()}
        </MetaRow>
        {call.ended_at && (
          <MetaRow icon={<PhoneOff className="h-3.5 w-3.5" />} label="Ended">
            {new Date(call.ended_at).toLocaleString()}
          </MetaRow>
        )}
        <MetaRow icon={<Bot className="h-3.5 w-3.5" />} label="Agent">
          {call.agent_id ? `Agent #${call.agent_id}` : "—"}
        </MetaRow>
        <MetaRow icon={<User className="h-3.5 w-3.5" />} label="Caller">
          {call.caller_identity}
        </MetaRow>
        {call.outcome && (
          <MetaRow icon={<CheckCircle2 className="h-3.5 w-3.5" />} label="Outcome">
            {call.outcome}
          </MetaRow>
        )}
        {call.escalation_reason && (
          <MetaRow icon={<ArrowUpRight className="h-3.5 w-3.5" />} label="Escalation">
            {call.escalation_reason}
          </MetaRow>
        )}
        <MetaRow label="LiveKit room">
          <span className="font-mono text-[11px] text-zinc-300">
            {call.livekit_room_id}
          </span>
        </MetaRow>
      </aside>
    </div>
  );
}

function TranscriptBubble({ turn }: { turn: CallTurn }) {
  const isUser = turn.role === "user";
  return (
    <li className={`flex gap-2.5 ${isUser ? "" : "flex-row-reverse"}`}>
      <div
        className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-[11px] ${
          isUser
            ? "bg-zinc-800 text-zinc-300"
            : "bg-accent-400/15 text-accent-300"
        }`}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>
      <div
        className={`max-w-[72%] rounded-xl border px-3.5 py-2.5 ${
          isUser
            ? "border-zinc-800 bg-zinc-900/60 text-zinc-100"
            : "border-accent-400/20 bg-accent-400/[0.06] text-zinc-100"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-5">{turn.text}</p>
        <p
          className={`mt-1 font-mono text-[10px] ${
            isUser ? "text-zinc-500" : "text-accent-300/70"
          }`}
        >
          {formatTs(turn.ts_ms)}
        </p>
      </div>
    </li>
  );
}

function ToolCallRow({ tc }: { tc: CallToolCall }) {
  const summaryArg = previewObject(tc.args_json);
  const summaryRes = previewObject(tc.result_json);
  return (
    <li className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 text-xs">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-1.5 font-mono font-medium text-zinc-100">
          <Wrench className="h-3.5 w-3.5 text-zinc-500" />
          {tc.tool_name}
        </span>
        <span className="flex items-center gap-2 text-zinc-500">
          <span className="font-mono tabular-nums">{tc.duration_ms}ms</span>
          {tc.status === "success" ? (
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
          )}
        </span>
      </div>
      {summaryArg && (
        <p className="mt-1.5 font-mono text-[11px] text-zinc-400">
          <span className="text-zinc-600">args</span> · {summaryArg}
        </p>
      )}
      {summaryRes && (
        <p className="font-mono text-[11px] text-zinc-400">
          <span className="text-zinc-600">result</span> · {summaryRes}
        </p>
      )}
      <p className="mt-1 font-mono text-[10px] text-zinc-600">at {formatTs(tc.ts_ms)}</p>
    </li>
  );
}

function MetaRow({
  icon,
  label,
  children,
}: {
  icon?: React.ReactNode;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 px-3 py-2">
      <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-zinc-500">
        {icon}
        {label}
      </div>
      <div className="mt-0.5 text-sm text-zinc-100">{children}</div>
    </div>
  );
}

function StatusDot({ status }: { status: CallStatus }) {
  const color =
    status === "active"
      ? "bg-accent-400 animate-pulse-glow"
      : status === "completed"
        ? "bg-emerald-400"
        : status === "escalated"
          ? "bg-violet-400"
          : "bg-rose-400";
  return <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${color}`} />;
}

function StatusBadge({ status }: { status: CallStatus }) {
  const styles: Record<CallStatus, string> = {
    completed: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    active: "bg-accent-400/10 text-accent-300 border-accent-400/30",
    escalated: "bg-violet-500/10 text-violet-300 border-violet-500/30",
    failed: "bg-rose-500/10 text-rose-300 border-rose-500/30",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${styles[status]}`}
    >
      {status}
    </span>
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
        <PhoneCall className="mb-3 h-6 w-6 text-zinc-600" />
        <h2 className="text-base font-medium text-zinc-200">{title}</h2>
        {body && <p className="mt-1 max-w-sm text-sm text-zinc-500">{body}</p>}
        {cta}
      </div>
    </div>
  );
}

function EmptyState({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="grid place-items-center py-20 text-center">
      <div className="mb-3 grid h-12 w-12 place-items-center rounded-full border border-zinc-800 bg-zinc-900/60 text-zinc-500">
        {icon}
      </div>
      <h2 className="text-base font-medium text-zinc-100">{title}</h2>
      <p className="mt-1 max-w-sm text-sm text-zinc-500">{body}</p>
    </div>
  );
}

function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

function formatTs(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function formatRelative(iso: string): string {
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const minutes = Math.round(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return date.toLocaleDateString();
}

function previewObject(obj: Record<string, unknown>): string {
  const entries = Object.entries(obj);
  if (entries.length === 0) return "";
  const repr = entries
    .slice(0, 3)
    .map(([k, v]) => `${k}=${typeof v === "string" ? `"${v}"` : JSON.stringify(v)}`)
    .join(", ");
  return repr.length > 120 ? `${repr.slice(0, 120)}...` : repr;
}
