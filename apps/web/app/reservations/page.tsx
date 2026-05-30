"use client";

import { useCallback, useEffect, useState } from "react";
import { BedDouble, CalendarDays, Phone, Plus, User, Users } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { ReadOnlyBanner } from "@/components/read-only-banner";
import { api } from "@/lib/api";
import type { Reservation } from "@/lib/types";

export default function ReservationsPage() {
  return (
    <AppShell>
      <ReservationsView />
    </AppShell>
  );
}

function ReservationsView() {
  const { currentWorkspaceId, workspaces, openNewWorkspaceModal, canEdit } = useAuth();
  const [items, setItems] = useState<Reservation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (currentWorkspaceId === null) {
      setItems(null);
      return;
    }
    setError(null);
    try {
      setItems(await api.listReservations(currentWorkspaceId, false));
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
            ? "Create your first workspace to manage reservations."
            : "Pick a workspace from the sidebar."
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

  async function setStatus(r: Reservation, status: "confirmed" | "cancelled") {
    if (currentWorkspaceId === null) return;
    try {
      await api.updateReservation(currentWorkspaceId, r.id, { status });
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const now = Date.now();
  const requested = (items ?? []).filter((r) => r.status === "requested");
  const confirmed = (items ?? []).filter((r) => r.status === "confirmed");
  const other = (items ?? []).filter(
    (r) => r.status === "cancelled" || new Date(r.check_out).getTime() < now
  );
  const active = [...requested, ...confirmed].filter(
    (r) => new Date(r.check_out).getTime() >= now
  );

  return (
    <div className="mx-auto max-w-4xl px-10 pb-16 pt-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
          Reservations
        </h1>
        <p className="mt-1 max-w-xl text-sm text-zinc-400">
          Room reservation requests taken by the concierge. Confirm or cancel
          each one.
        </p>
      </header>

      {error && (
        <p className="mb-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      )}

      <ReadOnlyBanner />

      {requested.length > 0 && (
        <section className="mb-8">
          <h2 className="mb-3 text-[11px] font-medium uppercase tracking-[0.14em] text-amber-300/80">
            Awaiting confirmation · {requested.length}
          </h2>
          <ul className="space-y-2">
            {requested.map((r) => (
              <ResRow
                key={r.id}
                r={r}
                onConfirm={canEdit ? () => setStatus(r, "confirmed") : undefined}
                onCancel={canEdit ? () => setStatus(r, "cancelled") : undefined}
              />
            ))}
          </ul>
        </section>
      )}

      <section className="mb-8">
        <h2 className="mb-3 text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
          Confirmed & upcoming · {confirmed.filter((r) => new Date(r.check_out).getTime() >= now).length}
        </h2>
        {items === null ? (
          <p className="text-sm text-zinc-500">Loading...</p>
        ) : active.filter((r) => r.status === "confirmed").length === 0 ? (
          <div className="grid place-items-center rounded-2xl border border-dashed border-zinc-800 px-6 py-12 text-center">
            <BedDouble className="mb-2 h-5 w-5 text-zinc-600" />
            <p className="text-sm text-zinc-300">No confirmed reservations</p>
            <p className="mt-1 text-xs text-zinc-500">
              Requests the concierge takes appear above for you to confirm.
            </p>
          </div>
        ) : (
          <ul className="space-y-2">
            {confirmed
              .filter((r) => new Date(r.check_out).getTime() >= now)
              .map((r) => (
                <ResRow
                  key={r.id}
                  r={r}
                  onCancel={canEdit ? () => setStatus(r, "cancelled") : undefined}
                />
              ))}
          </ul>
        )}
      </section>

      {other.length > 0 && (
        <section>
          <h2 className="mb-3 text-[11px] font-medium uppercase tracking-[0.14em] text-zinc-500">
            Past & cancelled · {other.length}
          </h2>
          <ul className="space-y-2 opacity-60">
            {other.slice(0, 20).map((r) => (
              <ResRow key={r.id} r={r} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function nights(checkIn: string, checkOut: string): number {
  const a = new Date(checkIn).getTime();
  const b = new Date(checkOut).getTime();
  return Math.max(1, Math.round((b - a) / 86_400_000));
}

function fmtDate(s: string): string {
  return new Date(s + "T00:00:00").toLocaleDateString([], {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function ResRow({
  r,
  onConfirm,
  onCancel,
}: {
  r: Reservation;
  onConfirm?: () => void;
  onCancel?: () => void;
}) {
  return (
    <li className="flex items-center gap-4 rounded-xl border border-zinc-800 bg-zinc-900/30 px-4 py-3">
      <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-zinc-800 text-accent-400">
        <BedDouble className="h-4 w-4" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-sm text-zinc-100">
          <User className="h-3.5 w-3.5 text-zinc-500" />
          {r.guest_name}
          {r.room_type && <span className="text-zinc-500">· {r.room_type}</span>}
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-zinc-500">
          <span className="flex items-center gap-1">
            <CalendarDays className="h-3 w-3" />
            {fmtDate(r.check_in)} → {fmtDate(r.check_out)} ({nights(r.check_in, r.check_out)}n)
          </span>
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            {r.num_guests}
          </span>
          {r.guest_phone && (
            <span className="flex items-center gap-1 font-mono">
              <Phone className="h-3 w-3" />
              {r.guest_phone}
            </span>
          )}
          {r.notes && <span className="italic">“{r.notes}”</span>}
        </div>
      </div>
      <StatusPill status={r.status} />
      {onConfirm && (
        <button
          type="button"
          onClick={onConfirm}
          className="rounded-lg border border-emerald-500/30 px-2.5 py-1.5 text-xs text-emerald-300 transition hover:bg-emerald-500/10"
        >
          Confirm
        </button>
      )}
      {onCancel && (
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-zinc-800 px-2.5 py-1.5 text-xs text-zinc-300 transition hover:border-rose-500/40 hover:text-rose-300"
        >
          Cancel
        </button>
      )}
    </li>
  );
}

function StatusPill({ status }: { status: string }) {
  const styles: Record<string, string> = {
    requested: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    confirmed: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    cancelled: "bg-rose-500/10 text-rose-300 border-rose-500/30",
  };
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${styles[status] ?? styles.requested}`}
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
        <BedDouble className="mb-3 h-6 w-6 text-zinc-600" />
        <h2 className="text-base font-medium text-zinc-200">{title}</h2>
        {body && <p className="mt-1 max-w-sm text-sm text-zinc-500">{body}</p>}
        {cta}
      </div>
    </div>
  );
}
