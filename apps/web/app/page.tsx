"use client";

import Link from "next/link";
import { ArrowUpRight, Plus, Radio } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { useLiveCalls } from "@/lib/use-live-calls";
import type { CallSummary } from "@/lib/types";

export default function HomePage() {
  return (
    <AppShell requires="admin">
      <LiveOperationsView />
    </AppShell>
  );
}

function LiveOperationsView() {
  const { currentWorkspaceId, workspaces, openNewWorkspaceModal } = useAuth();
  const calls = useLiveCalls(currentWorkspaceId);

  const active = calls.filter((c) => c.status === "active");
  const today = todayCalls(calls);
  const recent = calls.filter((c) => c.status !== "active").slice(0, 5);

  return (
    <div className="relative">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(ellipse_at_top,rgba(34,211,238,0.10),transparent_60%)]"
      />

      <div className="relative mx-auto max-w-6xl px-10 pb-16 pt-10">
        <header className="mb-10">
          <div className="mb-2 flex items-center gap-2">
            <span
              className={`relative inline-flex h-2 w-2 rounded-full ${
                active.length > 0
                  ? "bg-accent-400 animate-pulse-glow"
                  : "bg-zinc-700"
              }`}
            />
            <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
              {active.length > 0 ? "Live" : "Idle"}
            </span>
          </div>
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-100">
            {workspaces.length === 0
              ? "Welcome to VoiceOps."
              : active.length === 0
                ? "Nothing on the line right now."
                : `${active.length} active call${active.length === 1 ? "" : "s"}`}
          </h1>
          <p className="mt-2 max-w-xl text-sm text-zinc-400">
            {workspaces.length === 0
              ? "Create your first workspace to start configuring an agent and receiving calls."
              : "Real-time activity across your workspaces. Recent completed calls and today's snapshot below."}
          </p>
          {workspaces.length === 0 && (
            <button
              type="button"
              onClick={openNewWorkspaceModal}
              className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-accent-400 px-3.5 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300"
            >
              <Plus className="h-4 w-4" />
              Create your first workspace
            </button>
          )}
        </header>

        <section className="mb-12">
          {active.length === 0 ? (
            <EmptyActive />
          ) : (
            <ul className="grid gap-3 md:grid-cols-2">
              {active.map((c) => (
                <ActiveCallCard key={c.id} call={c} />
              ))}
            </ul>
          )}
        </section>

        <section className="mb-12">
          <SectionHeader title="Today" />
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="Calls" value={today.count.toString()} />
            <Stat label="Avg duration" value={today.avgDurationLabel} />
            <Stat label="Completed" value={today.completedCount.toString()} />
          </div>
        </section>

        <section>
          <SectionHeader
            title="Recent"
            trailing={
              recent.length > 0 ? (
                <Link
                  href="/calls"
                  className="group inline-flex items-center gap-1 text-xs text-zinc-400 transition hover:text-accent-400"
                >
                  All calls
                  <ArrowUpRight className="h-3 w-3 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </Link>
              ) : null
            }
          />
          {recent.length === 0 ? (
            <p className="rounded-xl border border-dashed border-zinc-800 px-4 py-8 text-center text-sm text-zinc-500">
              No completed calls yet. Try one from the Agent page.
            </p>
          ) : (
            <ul className="overflow-hidden rounded-xl border border-zinc-800">
              {recent.map((c, idx) => (
                <li key={c.id}>
                  <Link
                    href={`/calls?call=${c.id}`}
                    className={`flex items-center justify-between gap-4 px-4 py-3 text-sm transition hover:bg-zinc-900 ${
                      idx > 0 ? "border-t border-zinc-800/60" : ""
                    }`}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <span
                        className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotForStatus(c.status)}`}
                      />
                      <span className="truncate text-zinc-200">{c.caller_identity}</span>
                      <span className="hidden truncate font-mono text-[11px] text-zinc-600 sm:inline">
                        {c.livekit_room_id}
                      </span>
                    </div>
                    <div className="flex shrink-0 items-center gap-3 text-[11px] tabular-nums text-zinc-500">
                      <span>{formatDuration(c.duration_ms)}</span>
                      <span>{formatRelative(c.started_at)}</span>
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

function EmptyActive() {
  return (
    <div className="grid place-items-center rounded-2xl border border-zinc-800 bg-zinc-900/30 px-6 py-16">
      <Waveform />
      <p className="mt-6 text-sm text-zinc-400">Waiting for the next call.</p>
      <p className="mt-1 text-xs text-zinc-600">
        Active calls appear here in real time.
      </p>
    </div>
  );
}

function Waveform() {
  const bars = [10, 22, 14, 32, 18, 40, 24, 50, 18, 36, 14, 26, 10];
  return (
    <div className="flex h-14 items-center gap-1.5">
      {bars.map((h, i) => (
        <span
          key={i}
          className="w-1 rounded-full bg-zinc-700"
          style={{ height: `${h}px` }}
        />
      ))}
    </div>
  );
}

function ActiveCallCard({ call }: { call: CallSummary }) {
  return (
    <Link
      href={`/calls?call=${call.id}`}
      className="group rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 transition hover:border-accent-400/40 hover:bg-zinc-900"
    >
      <div className="mb-2 flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-accent-400 animate-pulse-glow" />
        <span className="text-[10px] font-medium uppercase tracking-wider text-accent-400">
          Live
        </span>
        <span className="ml-auto font-mono text-[11px] text-zinc-500">
          {call.livekit_room_id}
        </span>
      </div>
      <div className="text-sm text-zinc-100">{call.caller_identity}</div>
      <div className="mt-1 text-[11px] text-zinc-500">
        started {formatRelative(call.started_at)}
      </div>
    </Link>
  );
}

function SectionHeader({
  title,
  trailing,
}: {
  title: string;
  trailing?: React.ReactNode;
}) {
  return (
    <div className="mb-3 flex items-center justify-between">
      <h2 className="text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
        {title}
      </h2>
      {trailing}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/30 p-4">
      <div className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-zinc-100">
        {value}
      </div>
    </div>
  );
}

function todayCalls(all: CallSummary[]) {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const today = all.filter((c) => new Date(c.started_at) >= start);
  const completed = today.filter((c) => c.status === "completed");
  const totalMs = completed.reduce((acc, c) => acc + (c.duration_ms ?? 0), 0);
  const avgMs = completed.length > 0 ? Math.round(totalMs / completed.length) : 0;
  return {
    count: today.length,
    completedCount: completed.length,
    avgDurationLabel: completed.length === 0 ? "—" : formatDuration(avgMs),
  };
}

function dotForStatus(status: CallSummary["status"]): string {
  switch (status) {
    case "active":
      return "bg-accent-400";
    case "completed":
      return "bg-emerald-400";
    case "escalated":
      return "bg-violet-400";
    case "failed":
      return "bg-rose-400";
  }
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
