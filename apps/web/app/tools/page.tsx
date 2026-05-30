"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Plus,
  Save,
  Trash2,
  Wrench,
  Zap,
} from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { ReadOnlyBanner } from "@/components/read-only-banner";
import { api } from "@/lib/api";
import type { Tool, ToolCreate, ToolTestResponse } from "@/lib/types";

export default function ToolsPage() {
  return (
    <AppShell requires="admin">
      <ToolsView />
    </AppShell>
  );
}

function ToolsView() {
  const { currentWorkspaceId, workspaces, openNewWorkspaceModal, canEdit } = useAuth();
  const [tools, setTools] = useState<Tool[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (currentWorkspaceId === null) {
      setTools(null);
      return;
    }
    setError(null);
    try {
      const list = await api.listTools(currentWorkspaceId);
      setTools(list);
      setSelectedId((prev) => {
        if (prev !== null && list.some((t) => t.id === prev)) return prev;
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
            ? "Create your first workspace before defining tools."
            : "Pick a workspace from the sidebar to manage its tools."
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

  if (tools === null) {
    return <EmptyShell title="Loading tools..." body="" />;
  }

  const selected = tools.find((t) => t.id === selectedId) ?? null;

  return (
    <div className="mx-auto max-w-5xl px-10 pb-16 pt-10">
      <header className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
            Tools
          </h1>
          <p className="mt-1 max-w-xl text-sm text-zinc-400">
            Webhooks the agent can call mid-conversation — order lookups, account
            details, ticket creation. Each tool's description tells the LLM
            when to invoke it.
          </p>
        </div>
        {tools.length > 0 && canEdit && (
          <button
            type="button"
            onClick={() => setSelectedId(-1)}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 transition hover:border-zinc-700 hover:bg-zinc-800"
          >
            <Plus className="h-4 w-4" />
            New tool
          </button>
        )}
      </header>

      <ReadOnlyBanner />

      {error && (
        <p className="mb-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      )}

      <div className="grid gap-5 lg:grid-cols-[240px_1fr]">
        <aside className="space-y-1.5">
          {tools.length === 0 && selectedId !== -1 ? (
            <button
              type="button"
              onClick={() => setSelectedId(-1)}
              className="flex w-full items-center gap-2 rounded-xl border border-dashed border-zinc-800 px-3 py-4 text-left text-sm text-zinc-400 transition hover:border-accent-400/40 hover:text-zinc-200"
            >
              <Plus className="h-4 w-4 text-zinc-600" />
              Create your first tool
            </button>
          ) : null}
          {tools.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setSelectedId(t.id)}
              className={`flex w-full items-start gap-2.5 rounded-lg border px-3 py-3 text-left transition ${
                selectedId === t.id
                  ? "border-accent-400/40 bg-accent-400/[0.06]"
                  : "border-zinc-800 bg-zinc-900/30 hover:border-zinc-700 hover:bg-zinc-900"
              }`}
            >
              <Wrench
                className={`h-4 w-4 shrink-0 ${
                  selectedId === t.id ? "text-accent-400" : "text-zinc-500"
                }`}
              />
              <div className="min-w-0 flex-1">
                <div className="truncate font-mono text-sm text-zinc-100">
                  {t.name}
                </div>
                <div className="truncate text-[11px] text-zinc-500">
                  {hostname(t.webhook_url)}
                </div>
              </div>
            </button>
          ))}
        </aside>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6">
          {selectedId === -1 ? (
            <ToolForm
              key="new"
              workspaceId={currentWorkspaceId}
              tool={null}
              onSaved={reload}
              onCancel={() => setSelectedId(tools[0]?.id ?? null)}
            />
          ) : selected ? (
            <ToolForm
              key={selected.id}
              workspaceId={currentWorkspaceId}
              tool={selected}
              onSaved={reload}
              onDeleted={reload}
            />
          ) : (
            <EmptyState
              title="No tools yet"
              body="Create a webhook tool to extend what the agent can do mid-call."
              cta={
                <button
                  type="button"
                  onClick={() => setSelectedId(-1)}
                  className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-accent-400 px-3 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300"
                >
                  <Plus className="h-4 w-4" />
                  Create tool
                </button>
              }
            />
          )}
        </section>
      </div>

      <BuiltinsCallout />
    </div>
  );
}

function ToolForm({
  workspaceId,
  tool,
  onSaved,
  onDeleted,
  onCancel,
}: {
  workspaceId: number;
  tool: Tool | null;
  onSaved: () => Promise<void>;
  onDeleted?: () => Promise<void>;
  onCancel?: () => void;
}) {
  const [name, setName] = useState(tool?.name ?? "");
  const [description, setDescription] = useState(tool?.description ?? "");
  const [webhookUrl, setWebhookUrl] = useState(tool?.webhook_url ?? "");
  const [authHeader, setAuthHeader] = useState(tool?.auth_header ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testQuery, setTestQuery] = useState("");
  const [testResult, setTestResult] = useState<ToolTestResponse | null>(null);
  const [testing, setTesting] = useState(false);

  const isNew = tool === null;

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const payload: ToolCreate = {
      name: name.trim(),
      description: description.trim(),
      webhook_url: webhookUrl.trim(),
      auth_header: authHeader.trim() || null,
    };
    try {
      if (isNew) {
        await api.createTool(workspaceId, payload);
      } else {
        await api.updateTool(workspaceId, tool!.id, payload);
      }
      await onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function destroy() {
    if (!tool) return;
    if (!confirm(`Delete tool "${tool.name}"?`)) return;
    setSubmitting(true);
    try {
      await api.deleteTool(workspaceId, tool.id);
      await onDeleted?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setSubmitting(false);
    }
  }

  async function runTest() {
    if (!tool || !testQuery.trim()) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await api.testTool(workspaceId, tool.id, testQuery.trim());
      setTestResult(res);
    } catch (err) {
      setTestResult({
        status_code: 0,
        response_body: "",
        error: err instanceof Error ? err.message : String(err),
        duration_ms: 0,
      });
    } finally {
      setTesting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-6">
      <div>
        <h2 className="font-mono text-base text-zinc-100">
          {isNew ? "new_tool" : tool!.name}
        </h2>
        <p className="mt-0.5 text-xs text-zinc-500">
          {isNew
            ? "Define a webhook the agent can call mid-conversation."
            : `Created ${new Date(tool!.created_at).toLocaleString()}`}
        </p>
      </div>

      <Field label="Name" hint="snake_case identifier. The LLM sees this.">
        <input
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value.toLowerCase())}
          placeholder="lookup_order_status"
          className={`${inputClass} font-mono`}
        />
      </Field>

      <Field
        label="Description"
        hint="Tells the LLM when to call this. Be concrete: what it does, what args to pass, what it returns."
      >
        <textarea
          required
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          placeholder="Look up the status of a customer order by their order number or email. Returns shipping status, tracking link if available, and ETA."
          className={inputClass}
        />
      </Field>

      <Field label="Webhook URL" hint="POSTed with body {'query': <string>}.">
        <input
          type="url"
          required
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
          placeholder="https://api.your-client.com/lookup_order"
          className={`${inputClass} font-mono text-[12px]`}
        />
      </Field>

      <Field label="Authorization header" hint="Optional. Sent as `Authorization: <value>` on each call.">
        <input
          type="text"
          value={authHeader}
          onChange={(e) => setAuthHeader(e.target.value)}
          placeholder="Bearer ${'{your-token}'}"
          className={`${inputClass} font-mono text-[12px]`}
        />
      </Field>

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
            disabled={submitting || !name.trim() || !description.trim() || !webhookUrl.trim()}
            className="flex items-center gap-1.5 rounded-lg bg-accent-400 px-3.5 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {submitting ? "Saving..." : isNew ? "Create tool" : "Save changes"}
          </button>
        </div>
      </div>

      {!isNew && (
        <div className="border-t border-zinc-800 pt-5">
          <div className="mb-2 flex items-center gap-2">
            <Zap className="h-3.5 w-3.5 text-accent-400" />
            <span className="text-[11px] font-medium uppercase tracking-wider text-zinc-500">
              Live test
            </span>
          </div>
          <p className="mb-3 text-xs text-zinc-500">
            Send a sample <span className="font-mono text-zinc-400">query</span>{" "}
            to your webhook and inspect the response.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
              placeholder="order #12345"
              className={`${inputClass.replace("mt-2 ", "")} flex-1`}
            />
            <button
              type="button"
              onClick={runTest}
              disabled={!testQuery.trim() || testing}
              className="flex items-center gap-1.5 rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-100 transition hover:bg-zinc-700 disabled:opacity-50"
            >
              {testing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Zap className="h-4 w-4" />
              )}
              Run
            </button>
          </div>
          {testResult && (
            <div className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950/60 p-3 font-mono text-[11px]">
              <div className="mb-1.5 flex items-center justify-between">
                <span
                  className={
                    testResult.error
                      ? "text-rose-300"
                      : testResult.status_code >= 200 && testResult.status_code < 300
                        ? "text-emerald-300"
                        : "text-amber-300"
                  }
                >
                  {testResult.error
                    ? "error"
                    : `HTTP ${testResult.status_code}`}
                </span>
                <span className="tabular-nums text-zinc-500">
                  {testResult.duration_ms}ms
                </span>
              </div>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words text-zinc-300">
                {testResult.error || testResult.response_body || "(empty response)"}
              </pre>
            </div>
          )}
        </div>
      )}
    </form>
  );
}

function BuiltinsCallout() {
  return (
    <section className="mt-8 rounded-2xl border border-zinc-800 bg-zinc-900/30 p-6">
      <h2 className="mb-1 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
        Built-in tools
      </h2>
      <p className="mb-4 text-sm text-zinc-400">
        These are always available to every agent in this workspace. No
        configuration needed.
      </p>
      <ul className="space-y-2">
        <BuiltinRow
          name="search_knowledge_base"
          description="Searches the documents in the workspace knowledge base. The agent calls this for factual questions."
        />
        <BuiltinRow
          name="escalate_to_human"
          description="Hands the call off when the caller asks for a person, expresses frustration, or hits something out of scope. Marks the call as escalated and reads a polite handoff line."
        />
      </ul>
    </section>
  );
}

function BuiltinRow({ name, description }: { name: string; description: string }) {
  return (
    <li className="flex items-start gap-3 rounded-lg border border-zinc-800/80 bg-zinc-950/40 p-3">
      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
      <div className="min-w-0">
        <div className="font-mono text-sm text-zinc-100">{name}</div>
        <div className="mt-0.5 text-xs text-zinc-500">{description}</div>
      </div>
    </li>
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
        <Wrench className="mb-3 h-6 w-6 text-zinc-600" />
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
      <Wrench className="mb-3 h-6 w-6 text-zinc-600" />
      <h3 className="text-base font-medium text-zinc-100">{title}</h3>
      <p className="mt-1 max-w-sm text-sm text-zinc-500">{body}</p>
      {cta}
    </div>
  );
}

function hostname(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return url;
  }
}
