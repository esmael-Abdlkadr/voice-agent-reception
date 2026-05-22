"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Bot, Plus, Save, Trash2 } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { TestCallPanel } from "@/components/test-call-panel";
import { api } from "@/lib/api";
import type { Agent, AgentCreate } from "@/lib/types";

const LLM_MODELS = [
  { value: "llama-3.1-8b-instant", label: "Llama 3.1 8B Instant · Groq · fastest" },
  { value: "llama-3.3-70b-versatile", label: "Llama 3.3 70B Versatile · Groq · smarter" },
  { value: "llama-3.1-70b-versatile", label: "Llama 3.1 70B Versatile · Groq" },
];

const DEFAULT_CARTESIA_VOICE = "694f9389-aac1-45b6-b726-9d9369183238";

export default function AgentPage() {
  return (
    <AppShell>
      <AgentConfig />
    </AppShell>
  );
}

function AgentConfig() {
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
      setAgents(list);
      setSelectedId((prev) => {
        if (prev !== null && list.some((a) => a.id === prev)) return prev;
        return list[0]?.id ?? null;
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
            ? "Create your first workspace to start configuring an agent."
            : "Pick a workspace from the sidebar to manage its agent."
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
    <div className="mx-auto max-w-5xl px-10 pb-16 pt-10">
      <header className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
            Agent
          </h1>
          <p className="mt-1 text-sm text-zinc-400">
            How the AI receptionist sounds and behaves on this workspace's calls.
          </p>
        </div>
        {agents.length > 0 && (
          <button
            type="button"
            onClick={() => setSelectedId(-1)}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 transition hover:border-zinc-700 hover:bg-zinc-800"
          >
            <Plus className="h-4 w-4" />
            New agent
          </button>
        )}
      </header>

      {error && (
        <p className="mb-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      )}

      <div className="grid gap-5 lg:grid-cols-[240px_1fr]">
        <aside className="space-y-1.5">
          {agents.length === 0 && selectedId !== -1 ? (
            <button
              type="button"
              onClick={() => setSelectedId(-1)}
              className="flex w-full items-center gap-2 rounded-xl border border-dashed border-zinc-800 px-3 py-4 text-left text-sm text-zinc-400 transition hover:border-accent-400/40 hover:text-zinc-200"
            >
              <Plus className="h-4 w-4 text-zinc-600" />
              Create your first agent
            </button>
          ) : null}
          {agents.map((agent) => (
            <button
              key={agent.id}
              type="button"
              onClick={() => setSelectedId(agent.id)}
              className={`flex w-full items-start gap-2.5 rounded-lg border px-3 py-3 text-left transition ${
                selectedId === agent.id
                  ? "border-accent-400/40 bg-accent-400/[0.06]"
                  : "border-zinc-800 bg-zinc-900/30 hover:border-zinc-700 hover:bg-zinc-900"
              }`}
            >
              <Bot
                className={`h-4 w-4 shrink-0 ${
                  selectedId === agent.id ? "text-accent-400" : "text-zinc-500"
                }`}
              />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-zinc-100">
                  {agent.name}
                </div>
                <div className="truncate text-[11px] text-zinc-500">
                  {agent.is_active ? "active" : "inactive"} · {agent.llm_model}
                </div>
              </div>
            </button>
          ))}
        </aside>

        <section className="space-y-5">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6">
            {selectedId === -1 ? (
              <AgentForm
                key="new"
                workspaceId={currentWorkspaceId}
                agent={null}
                onSaved={async () => {
                  await reload();
                }}
                onCancel={() => setSelectedId(agents[0]?.id ?? null)}
              />
            ) : selected ? (
              <AgentForm
                key={selected.id}
                workspaceId={currentWorkspaceId}
                agent={selected}
                onSaved={async () => {
                  await reload();
                }}
                onDeleted={async () => {
                  await reload();
                }}
              />
            ) : (
              <EmptyState
                title="No agents yet"
                body="Create an agent to start receiving calls in this workspace."
                cta={
                  <button
                    type="button"
                    onClick={() => setSelectedId(-1)}
                    className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-accent-400 px-3 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300"
                  >
                    <Plus className="h-4 w-4" />
                    Create agent
                  </button>
                }
              />
            )}
          </div>

          {selected && selected.is_active && (
            <TestCallPanel
              workspaceId={currentWorkspaceId}
              agentId={selected.id}
              agentName={selected.name}
            />
          )}
        </section>
      </div>
    </div>
  );
}

function AgentForm({
  workspaceId,
  agent,
  onSaved,
  onDeleted,
  onCancel,
}: {
  workspaceId: number;
  agent: Agent | null;
  onSaved: () => Promise<void>;
  onDeleted?: () => Promise<void>;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(agent?.name ?? "");
  const [greeting, setGreeting] = useState(agent?.greeting ?? "");
  const [persona, setPersona] = useState(agent?.persona_prompt ?? "");
  const [voiceId, setVoiceId] = useState(agent?.voice_id || DEFAULT_CARTESIA_VOICE);
  const [llmModel, setLlmModel] = useState(agent?.llm_model ?? LLM_MODELS[0].value);
  const [isActive, setIsActive] = useState(agent?.is_active ?? true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isNew = agent === null;

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const payload: AgentCreate = {
      name: name.trim(),
      greeting,
      persona_prompt: persona,
      voice_id: voiceId.trim(),
      llm_model: llmModel,
      is_active: isActive,
    };
    try {
      if (isNew) {
        await api.createAgent(workspaceId, payload);
      } else {
        await api.updateAgent(workspaceId, agent!.id, payload);
      }
      await onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function destroy() {
    if (!agent) return;
    if (!confirm(`Delete agent "${agent.name}"?`)) return;
    setSubmitting(true);
    try {
      await api.deleteAgent(workspaceId, agent.id);
      await onDeleted?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      <div>
        <h2 className="text-base font-medium text-zinc-100">
          {isNew ? "New agent" : agent!.name}
        </h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          {isNew
            ? "Configure the agent that will answer calls."
            : `Last updated ${new Date(agent!.updated_at).toLocaleString()}`}
        </p>
      </div>

      <Field label="Name" hint="Internal label. Customers never hear this.">
        <input
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Support Agent"
          className={inputClass}
        />
      </Field>

      <Field
        label="Greeting"
        hint="The first thing callers hear. Short and warm."
      >
        <textarea
          value={greeting}
          onChange={(e) => setGreeting(e.target.value)}
          rows={2}
          placeholder="Thanks for calling Acme Support, how can I help?"
          className={inputClass}
        />
      </Field>

      <Field
        label="Persona prompt"
        hint="System instructions for tone, scope, and guardrails."
      >
        <textarea
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          rows={8}
          placeholder="You are a friendly customer support agent for Acme. Stay focused on Acme product questions. Escalate billing issues to a human..."
          className={`${inputClass} font-mono text-[13px]`}
        />
      </Field>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="Cartesia voice ID" hint="Paste a Cartesia voice UUID.">
          <input
            type="text"
            value={voiceId}
            onChange={(e) => setVoiceId(e.target.value)}
            placeholder={DEFAULT_CARTESIA_VOICE}
            className={`${inputClass} font-mono text-[12px]`}
          />
        </Field>
        <Field label="LLM model" hint="Powers reasoning + tool use.">
          <select
            value={llmModel}
            onChange={(e) => setLlmModel(e.target.value)}
            className={inputClass}
          >
            {LLM_MODELS.map((m) => (
              <option key={m.value} value={m.value} className="bg-zinc-900">
                {m.label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <label className="flex items-center gap-2 text-sm text-zinc-300">
        <input
          type="checkbox"
          checked={isActive}
          onChange={(e) => setIsActive(e.target.checked)}
          className="h-4 w-4 rounded border-zinc-700 bg-zinc-900 accent-accent-400"
        />
        Active — route incoming calls to this agent
      </label>

      {error && (
        <p className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      )}

      <div className="flex items-center justify-between border-t border-zinc-800 pt-5">
        <div>
          {!isNew && onDeleted && (
            <button
              type="button"
              onClick={destroy}
              disabled={submitting}
              className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 px-3 py-2 text-sm text-rose-300 transition hover:bg-rose-500/10 disabled:opacity-60"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          )}
        </div>
        <div className="flex gap-2">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="rounded-lg px-3 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-200"
            >
              Cancel
            </button>
          )}
          <button
            type="submit"
            disabled={submitting || !name.trim()}
            className="flex items-center gap-1.5 rounded-lg bg-accent-400 px-3.5 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {submitting ? "Saving..." : isNew ? "Create agent" : "Save changes"}
          </button>
        </div>
      </div>
    </form>
  );
}

const inputClass =
  "mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none transition focus:border-accent-400/60 focus:shadow-glow";

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-[11px] font-medium uppercase tracking-wider text-zinc-500">
        {label}
      </label>
      {children}
      {hint && <p className="mt-1.5 text-[11px] text-zinc-500">{hint}</p>}
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
        <Bot className="mb-3 h-6 w-6 text-zinc-600" />
        <h2 className="text-base font-medium text-zinc-200">{title}</h2>
        {body && <p className="mt-1 max-w-sm text-sm text-zinc-500">{body}</p>}
        {cta}
      </div>
    </div>
  );
}

function EmptyState({
  title,
  body,
  cta,
}: {
  title: string;
  body: string;
  cta?: React.ReactNode;
}) {
  return (
    <div className="grid place-items-center py-12 text-center">
      <Bot className="mb-3 h-6 w-6 text-zinc-600" />
      <h3 className="text-base font-medium text-zinc-100">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-zinc-500">{body}</p>
      {cta}
    </div>
  );
}
