"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  Bot,
  Phone,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { ReadOnlyBanner } from "@/components/read-only-banner";
import { api } from "@/lib/api";
import type { Agent, PhoneNumber } from "@/lib/types";

export default function NumbersPage() {
  return (
    <AppShell requires="admin">
      <NumbersView />
    </AppShell>
  );
}

function NumbersView() {
  const { currentWorkspaceId, workspaces, openNewWorkspaceModal, canEdit } = useAuth();
  const [numbers, setNumbers] = useState<PhoneNumber[] | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const reload = useCallback(async () => {
    if (currentWorkspaceId === null) {
      setNumbers(null);
      return;
    }
    setError(null);
    try {
      const [nums, ags] = await Promise.all([
        api.listPhoneNumbers(currentWorkspaceId),
        api.listAgents(currentWorkspaceId),
      ]);
      setNumbers(nums);
      setAgents(ags);
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
            ? "Create your first workspace before adding phone numbers."
            : "Pick a workspace from the sidebar to manage its phone numbers."
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

  async function setAgent(num: PhoneNumber, agentId: number | null) {
    if (currentWorkspaceId === null) return;
    try {
      await api.updatePhoneNumber(currentWorkspaceId, num.id, { agent_id: agentId });
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function toggleActive(num: PhoneNumber) {
    if (currentWorkspaceId === null) return;
    try {
      await api.updatePhoneNumber(currentWorkspaceId, num.id, {
        is_active: !num.is_active,
      });
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function remove(num: PhoneNumber) {
    if (currentWorkspaceId === null) return;
    if (!confirm(`Remove ${num.e164}? Calls to it will stop routing to an agent.`)) {
      return;
    }
    try {
      await api.deletePhoneNumber(currentWorkspaceId, num.id);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-10 pb-16 pt-10">
      <header className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
            Numbers
          </h1>
          <p className="mt-1 max-w-xl text-sm text-zinc-400">
            Phone numbers that route to this workspace's agents. Each incoming
            call is answered by the agent you assign here.
          </p>
        </div>
        {numbers && numbers.length > 0 && canEdit && (
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 transition hover:border-zinc-700 hover:bg-zinc-800"
          >
            <Plus className="h-4 w-4" />
            Add number
          </button>
        )}
      </header>

      {error && (
        <p className="mb-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      )}

      <ReadOnlyBanner />

      {adding && (
        <AddNumberForm
          workspaceId={currentWorkspaceId}
          agents={agents}
          onClose={() => setAdding(false)}
          onCreated={async () => {
            setAdding(false);
            await reload();
          }}
        />
      )}

      {numbers === null ? (
        <p className="text-sm text-zinc-500">Loading...</p>
      ) : numbers.length === 0 && !adding ? (
        <div className="grid place-items-center rounded-2xl border border-dashed border-zinc-800 px-6 py-16 text-center">
          <Phone className="mb-3 h-6 w-6 text-zinc-600" />
          <h2 className="text-base font-medium text-zinc-200">No numbers yet</h2>
          <p className="mt-1 max-w-md text-sm text-zinc-500">
            Provision a number with your telephony provider (e.g. Twilio), point
            its SIP trunk at LiveKit, then register it here so calls reach an agent.
          </p>
          <button
            type="button"
            onClick={() => setAdding(true)}
            className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-accent-400 px-3.5 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300"
          >
            <Plus className="h-4 w-4" />
            Add your first number
          </button>
        </div>
      ) : (
        <ul className="space-y-2.5">
          {numbers!.map((num) => {
            const agent = agents.find((a) => a.id === num.agent_id);
            return (
              <li
                key={num.id}
                className="flex items-center gap-4 rounded-xl border border-zinc-800 bg-zinc-900/30 px-4 py-3.5"
              >
                <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-zinc-800 text-accent-400">
                  <Phone className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-zinc-100">{num.e164}</span>
                    {!num.is_active && (
                      <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-zinc-500">
                        inactive
                      </span>
                    )}
                  </div>
                  <div className="truncate text-[11px] text-zinc-500">
                    {num.label || "—"} · {num.provider}
                  </div>
                </div>

                {/* Agent assignment */}
                <div className="flex items-center gap-1.5">
                  <Bot className="h-3.5 w-3.5 text-zinc-500" />
                  <select
                    value={num.agent_id ?? ""}
                    onChange={(e) =>
                      setAgent(num, e.target.value ? Number(e.target.value) : null)
                    }
                    className="rounded-lg border border-zinc-800 bg-zinc-950 px-2.5 py-1.5 text-xs text-zinc-100 outline-none focus:border-accent-400/60"
                  >
                    <option value="" className="bg-zinc-900">
                      Auto (first active)
                    </option>
                    {agents.map((a) => (
                      <option key={a.id} value={a.id} className="bg-zinc-900">
                        {a.name}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  onClick={() => toggleActive(num)}
                  className="rounded-lg border border-zinc-800 px-2.5 py-1.5 text-xs text-zinc-300 transition hover:bg-zinc-800"
                >
                  {num.is_active ? "Disable" : "Enable"}
                </button>
                <button
                  type="button"
                  onClick={() => remove(num)}
                  className="rounded-lg p-1.5 text-zinc-500 transition hover:bg-rose-500/10 hover:text-rose-300"
                  aria-label="Remove number"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <SetupHint />
    </div>
  );
}

function AddNumberForm({
  workspaceId,
  agents,
  onClose,
  onCreated,
}: {
  workspaceId: number;
  agents: Agent[];
  onClose: () => void;
  onCreated: () => Promise<void>;
}) {
  const [e164, setE164] = useState("");
  const [label, setLabel] = useState("");
  const [agentId, setAgentId] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await api.createPhoneNumber(workspaceId, {
        e164: e164.trim(),
        label: label.trim(),
        agent_id: agentId ? Number(agentId) : null,
      });
      await onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="mb-5 rounded-xl border border-zinc-800 bg-zinc-900/40 p-5"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-sm font-medium text-zinc-100">Add a phone number</h2>
        <button
          type="button"
          onClick={onClose}
          className="rounded p-1 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-300"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="sm:col-span-1">
          <label className="block text-[11px] font-medium uppercase tracking-wider text-zinc-500">
            Number (E.164)
          </label>
          <input
            type="text"
            required
            value={e164}
            onChange={(e) => setE164(e.target.value)}
            placeholder="+19859996931"
            className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm font-mono text-zinc-100 placeholder:text-zinc-600 outline-none focus:border-accent-400/60 focus:shadow-glow"
          />
        </div>
        <div className="sm:col-span-1">
          <label className="block text-[11px] font-medium uppercase tracking-wider text-zinc-500">
            Label
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="Main line"
            className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none focus:border-accent-400/60 focus:shadow-glow"
          />
        </div>
        <div className="sm:col-span-1">
          <label className="block text-[11px] font-medium uppercase tracking-wider text-zinc-500">
            Answering agent
          </label>
          <select
            value={agentId}
            onChange={(e) => setAgentId(e.target.value)}
            className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-accent-400/60"
          >
            <option value="" className="bg-zinc-900">
              Auto (first active)
            </option>
            {agents.map((a) => (
              <option key={a.id} value={a.id} className="bg-zinc-900">
                {a.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {error && (
        <p className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
          {error}
        </p>
      )}
      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg px-3 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting || !e164.trim()}
          className="rounded-lg bg-accent-400 px-3.5 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300 disabled:opacity-50"
        >
          {submitting ? "Adding..." : "Add number"}
        </button>
      </div>
    </form>
  );
}

function SetupHint() {
  return (
    <div className="mt-8 rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6">
      <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
        How routing works
      </h2>
      <ol className="mt-3 space-y-2 text-sm text-zinc-400">
        <li className="flex gap-2">
          <span className="font-mono text-zinc-600">1.</span>
          Provision a number with your provider (Twilio) and point its SIP trunk
          origination at your LiveKit SIP URI.
        </li>
        <li className="flex gap-2">
          <span className="font-mono text-zinc-600">2.</span>
          Register the number here in E.164 format and assign the agent that
          should answer it.
        </li>
        <li className="flex gap-2">
          <span className="font-mono text-zinc-600">3.</span>
          Incoming calls are matched to the number, the assigned agent answers,
          and the call appears live under Calls.
        </li>
      </ol>
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
        <Phone className="mb-3 h-6 w-6 text-zinc-600" />
        <h2 className="text-base font-medium text-zinc-200">{title}</h2>
        {body && <p className="mt-1 max-w-sm text-sm text-zinc-500">{body}</p>}
        {cta}
      </div>
    </div>
  );
}
