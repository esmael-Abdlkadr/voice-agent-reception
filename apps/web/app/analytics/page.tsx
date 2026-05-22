"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { BarChart3, Clock, Plus, Wrench } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { api } from "@/lib/api";
import type { WorkspaceAnalytics } from "@/lib/types";

const RANGES = [
  { days: 7, label: "7d" },
  { days: 30, label: "30d" },
  { days: 90, label: "90d" },
];

export default function AnalyticsPage() {
  return (
    <AppShell>
      <AnalyticsView />
    </AppShell>
  );
}

function AnalyticsView() {
  const { currentWorkspaceId, workspaces, openNewWorkspaceModal } = useAuth();
  const [days, setDays] = useState(30);
  const [data, setData] = useState<WorkspaceAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (currentWorkspaceId === null) {
      setData(null);
      return;
    }
    setError(null);
    try {
      const res = await api.workspaceAnalytics(currentWorkspaceId, days);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [currentWorkspaceId, days]);

  useEffect(() => {
    reload();
  }, [reload]);

  if (currentWorkspaceId === null) {
    return (
      <EmptyShell
        title={workspaces.length === 0 ? "No workspaces yet" : "No workspace selected"}
        body={
          workspaces.length === 0
            ? "Create your first workspace to see analytics."
            : "Pick a workspace from the sidebar to view its analytics."
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
    <div className="mx-auto max-w-6xl px-10 pb-16 pt-10">
      <header className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
            Analytics
          </h1>
          <p className="mt-1 text-sm text-zinc-400">
            Volume, quality, and efficiency for this workspace.
          </p>
        </div>
        <div className="flex items-center gap-1 rounded-lg border border-zinc-800 bg-zinc-900/60 p-0.5">
          {RANGES.map((r) => {
            const active = days === r.days;
            return (
              <button
                key={r.days}
                type="button"
                onClick={() => setDays(r.days)}
                className={`rounded-md px-3 py-1 text-xs transition ${
                  active
                    ? "bg-zinc-100 text-zinc-900"
                    : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
                }`}
              >
                {r.label}
              </button>
            );
          })}
        </div>
      </header>

      {error && (
        <p className="mb-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      )}

      {data === null ? (
        <p className="text-sm text-zinc-500">Loading analytics...</p>
      ) : data.total_calls === 0 ? (
        <EmptyData days={days} />
      ) : (
        <>
          <section className="mb-10 grid gap-3 sm:grid-cols-3">
            <BigStat
              label="Total calls"
              value={data.total_calls.toLocaleString()}
              sub={`last ${days} days`}
            />
            <BigStat
              label="Avg duration"
              value={formatDuration(data.avg_duration_ms)}
              sub="completed + escalated"
            />
            <BigStat
              label="Completion rate"
              value={formatPercent(data.completion_rate)}
              sub="completed / finished"
              tone={completionTone(data.completion_rate)}
            />
          </section>

          <section className="mb-10 rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6">
            <SectionHeader title="Calls per day" />
            <DailyBars by_day={data.by_day} />
          </section>

          <section className="mb-10 rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6">
            <SectionHeader title="Outcomes" />
            <StatusBar by_status={data.by_status} />
          </section>

          <section className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6">
            <SectionHeader title="Top tools" />
            <TopTools tools={data.top_tools} />
          </section>
        </>
      )}
    </div>
  );
}

function BigStat({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  const valueColor =
    tone === "good"
      ? "text-emerald-300"
      : tone === "warn"
        ? "text-amber-300"
        : tone === "bad"
          ? "text-rose-300"
          : "text-zinc-100";
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-5">
      <div className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
        {label}
      </div>
      <div className={`mt-1.5 text-3xl font-semibold tabular-nums ${valueColor}`}>
        {value}
      </div>
      {sub && <div className="mt-1 text-[11px] text-zinc-500">{sub}</div>}
    </div>
  );
}

function SectionHeader({ title }: { title: string }) {
  return (
    <h2 className="mb-4 text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
      {title}
    </h2>
  );
}

function DailyBars({ by_day }: { by_day: WorkspaceAnalytics["by_day"] }) {
  const max = Math.max(1, ...by_day.map((d) => d.count));
  return (
    <div>
      <div className="flex h-32 items-end gap-1">
        {by_day.map((point) => {
          const heightPct = (point.count / max) * 100;
          const isZero = point.count === 0;
          return (
            <div
              key={point.date}
              className="group relative flex flex-1 items-end"
              title={`${point.date} · ${point.count} call${point.count === 1 ? "" : "s"}`}
            >
              <div
                className={`w-full rounded-sm transition-all ${
                  isZero
                    ? "bg-zinc-800/60"
                    : "bg-gradient-to-t from-accent-600/50 to-accent-400/90"
                }`}
                style={{ height: isZero ? "2px" : `${Math.max(heightPct, 4)}%` }}
              />
              <div className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-1.5 hidden -translate-x-1/2 whitespace-nowrap rounded border border-zinc-800 bg-zinc-950 px-2 py-1 text-[10px] text-zinc-300 group-hover:block">
                {point.date}
                <span className="ml-2 font-mono text-accent-400">
                  {point.count}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-2 flex justify-between font-mono text-[10px] text-zinc-600">
        <span>{by_day[0]?.date}</span>
        <span>{by_day[by_day.length - 1]?.date}</span>
      </div>
    </div>
  );
}

function StatusBar({
  by_status,
}: {
  by_status: WorkspaceAnalytics["by_status"];
}) {
  const total =
    by_status.completed + by_status.active + by_status.escalated + by_status.failed;
  if (total === 0) {
    return <p className="text-sm text-zinc-500">No data.</p>;
  }
  const segments = [
    { key: "completed", count: by_status.completed, color: "bg-emerald-400", label: "completed" },
    { key: "escalated", count: by_status.escalated, color: "bg-violet-400", label: "escalated" },
    { key: "failed", count: by_status.failed, color: "bg-rose-400", label: "failed" },
    { key: "active", count: by_status.active, color: "bg-accent-400", label: "active" },
  ].filter((s) => s.count > 0);

  return (
    <div>
      <div className="mb-3 flex h-3 w-full overflow-hidden rounded-full bg-zinc-900">
        {segments.map((s) => {
          const widthPct = (s.count / total) * 100;
          return (
            <div
              key={s.key}
              className={s.color}
              style={{ width: `${widthPct}%` }}
              title={`${s.label}: ${s.count}`}
            />
          );
        })}
      </div>
      <ul className="grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4">
        {segments.map((s) => {
          const pct = (s.count / total) * 100;
          return (
            <li key={s.key} className="flex items-center gap-2 text-xs">
              <span className={`h-2 w-2 rounded-full ${s.color}`} />
              <span className="text-zinc-300 capitalize">{s.label}</span>
              <span className="ml-auto font-mono tabular-nums text-zinc-500">
                {s.count}
                <span className="ml-1 text-[10px] text-zinc-600">
                  · {pct.toFixed(0)}%
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function TopTools({
  tools,
}: {
  tools: WorkspaceAnalytics["top_tools"];
}) {
  if (tools.length === 0) {
    return (
      <p className="text-sm text-zinc-500">
        No tool calls in this window. Tools usage shows up here once the
        agent starts invoking them.
      </p>
    );
  }
  const max = Math.max(...tools.map((t) => t.count));
  return (
    <ul className="space-y-3">
      {tools.map((t) => {
        const pct = (t.count / max) * 100;
        return (
          <li key={t.tool_name}>
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="flex items-center gap-1.5 font-mono text-zinc-200">
                <Wrench className="h-3.5 w-3.5 text-zinc-500" />
                {t.tool_name}
              </span>
              <span className="font-mono tabular-nums text-zinc-400">
                {t.count}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-zinc-900">
              <div
                className="h-full bg-gradient-to-r from-accent-600/40 to-accent-400"
                style={{ width: `${pct}%` }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function EmptyData({ days }: { days: number }) {
  return (
    <div className="grid place-items-center rounded-2xl border border-dashed border-zinc-800 px-6 py-20 text-center">
      <BarChart3 className="mb-3 h-6 w-6 text-zinc-600" />
      <h2 className="text-base font-medium text-zinc-200">
        No call data in the last {days} days
      </h2>
      <p className="mt-1 max-w-sm text-sm text-zinc-500">
        Run a test call from the Agent page to populate this view.
      </p>
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
        <BarChart3 className="mb-3 h-6 w-6 text-zinc-600" />
        <h2 className="text-base font-medium text-zinc-200">{title}</h2>
        {body && <p className="mt-1 max-w-sm text-sm text-zinc-500">{body}</p>}
        {cta}
      </div>
    </div>
  );
}

function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  const totalSeconds = Math.round(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

function formatPercent(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

function completionTone(rate: number): "good" | "warn" | "bad" | "default" {
  if (rate >= 0.85) return "good";
  if (rate >= 0.6) return "warn";
  if (rate > 0) return "bad";
  return "default";
}
