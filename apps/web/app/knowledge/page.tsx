"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Loader2,
  Plus,
  Search,
  Trash2,
  Upload,
} from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { useAuth } from "@/components/auth-provider";
import { ReadOnlyBanner } from "@/components/read-only-banner";
import { api } from "@/lib/api";
import type { KnowledgeDoc, KnowledgeSearchHit, KnowledgeStatus } from "@/lib/types";

export default function KnowledgePage() {
  return (
    <AppShell requires="admin">
      <KnowledgeView />
    </AppShell>
  );
}

function KnowledgeView() {
  const { currentWorkspaceId, workspaces, openNewWorkspaceModal, canEdit } = useAuth();
  const [docs, setDocs] = useState<KnowledgeDoc[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const reload = useCallback(async () => {
    if (currentWorkspaceId === null) {
      setDocs(null);
      return;
    }
    try {
      const list = await api.listKnowledge(currentWorkspaceId);
      setDocs(list);
      setSelectedId((prev) =>
        prev !== null && list.some((d) => d.id === prev) ? prev : list[0]?.id ?? null
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [currentWorkspaceId]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (!docs || currentWorkspaceId === null) return;
    if (!docs.some((d) => d.status === "processing")) return;
    const handle = window.setInterval(reload, 2000);
    return () => window.clearInterval(handle);
  }, [docs, currentWorkspaceId, reload]);

  if (currentWorkspaceId === null) {
    return (
      <EmptyShell
        title={workspaces.length === 0 ? "No workspaces yet" : "No workspace selected"}
        body={
          workspaces.length === 0
            ? "Create your first workspace before uploading knowledge."
            : "Pick a workspace from the sidebar to manage its knowledge base."
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

  async function onPickFile(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || currentWorkspaceId === null) return;
    setUploading(true);
    setError(null);
    try {
      const doc = await api.uploadKnowledge(currentWorkspaceId, file);
      await reload();
      setSelectedId(doc.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }

  async function onDelete(doc: KnowledgeDoc) {
    if (currentWorkspaceId === null) return;
    if (!confirm(`Delete "${doc.filename}"? Its embeddings will be removed too.`)) {
      return;
    }
    try {
      await api.deleteKnowledge(currentWorkspaceId, doc.id);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const selected = docs?.find((d) => d.id === selectedId) ?? null;

  return (
    <div className="mx-auto max-w-6xl px-10 pb-16 pt-10">
      <header className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
            Knowledge
          </h1>
          <p className="mt-1 max-w-xl text-sm text-zinc-400">
            Upload the docs your agent should know. Embeddings are computed
            locally and stored in this workspace's Qdrant collection.
          </p>
        </div>
        {canEdit && (
          <div>
            <input
              ref={inputRef}
              type="file"
              accept=".txt,.md,.pdf"
              className="hidden"
              onChange={onPickFile}
            />
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              disabled={uploading}
              className="flex items-center gap-1.5 rounded-lg bg-accent-400 px-3.5 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300 disabled:opacity-60"
            >
              {uploading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Upload className="h-4 w-4" />
              )}
              {uploading ? "Uploading..." : "Upload document"}
            </button>
          </div>
        )}
      </header>

      {error && (
        <p className="mb-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
          {error}
        </p>
      )}

      <ReadOnlyBanner />

      <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
        <aside className="space-y-1.5">
          {docs === null ? (
            <p className="px-3 py-2 text-sm text-zinc-500">Loading...</p>
          ) : docs.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-zinc-800 p-8 text-center">
              <BookOpen className="mx-auto mb-2 h-5 w-5 text-zinc-600" />
              <p className="text-sm text-zinc-300">No documents yet.</p>
              <p className="mt-1 text-xs text-zinc-500">
                Upload a .txt, .md, or .pdf to get started.
              </p>
            </div>
          ) : (
            docs.map((doc) => (
              <button
                key={doc.id}
                type="button"
                onClick={() => setSelectedId(doc.id)}
                className={`flex w-full items-start gap-2.5 rounded-lg border px-3 py-3 text-left transition ${
                  selectedId === doc.id
                    ? "border-accent-400/40 bg-accent-400/[0.06]"
                    : "border-zinc-800 bg-zinc-900/30 hover:border-zinc-700 hover:bg-zinc-900"
                }`}
              >
                <StatusIcon status={doc.status} />
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-zinc-100">
                    {doc.filename}
                  </div>
                  <div className="truncate text-[11px] text-zinc-500">
                    {formatBytes(doc.size_bytes)} ·{" "}
                    {doc.status === "ready"
                      ? `${doc.chunk_count} chunks`
                      : doc.status}
                  </div>
                </div>
              </button>
            ))
          )}
        </aside>

        <section className="rounded-2xl border border-zinc-800 bg-zinc-900/30">
          {selected ? (
            <DocDetail
              doc={selected}
              workspaceId={currentWorkspaceId}
              onDelete={onDelete}
            />
          ) : (
            <div className="grid place-items-center py-16 text-center">
              <BookOpen className="mb-2 h-5 w-5 text-zinc-600" />
              <p className="text-sm font-medium text-zinc-200">
                Select a document to view details and search it
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function DocDetail({
  doc,
  workspaceId,
  onDelete,
}: {
  doc: KnowledgeDoc;
  workspaceId: number;
  onDelete: (doc: KnowledgeDoc) => Promise<void>;
}) {
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<KnowledgeSearchHit[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  async function runSearch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    setSearchError(null);
    try {
      const res = await api.searchKnowledge(workspaceId, query.trim());
      setHits(res.hits);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : String(err));
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="divide-y divide-zinc-800/80">
      <div className="flex items-start justify-between gap-4 p-6">
        <div className="min-w-0">
          <h2 className="truncate text-base font-medium text-zinc-100">
            {doc.filename}
          </h2>
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500">
            <StatusBadge status={doc.status} />
            <span>{formatBytes(doc.size_bytes)}</span>
            <span>{doc.chunk_count} chunks</span>
            <span>uploaded {new Date(doc.created_at).toLocaleString()}</span>
          </div>
        </div>
        <button
          type="button"
          onClick={() => onDelete(doc)}
          className="flex items-center gap-1.5 rounded-lg border border-rose-500/30 px-3 py-1.5 text-xs text-rose-300 transition hover:bg-rose-500/10"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Delete
        </button>
      </div>

      <div className="p-6">
        <h3 className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-zinc-500">
          Search test
        </h3>
        <p className="mb-3 text-xs text-zinc-500">
          Try a question your agent might be asked. Runs across all docs in this
          workspace.
        </p>
        <form onSubmit={runSearch} className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. How do I reset my password?"
            disabled={doc.status !== "ready"}
            className="flex-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none transition focus:border-accent-400/60 focus:shadow-glow disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!query.trim() || searching || doc.status !== "ready"}
            className="flex items-center gap-1.5 rounded-lg bg-accent-400 px-3 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300 disabled:opacity-50"
          >
            {searching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Search className="h-4 w-4" />
            )}
            Search
          </button>
        </form>
        {doc.status !== "ready" && (
          <p className="mt-2 text-xs text-amber-400/80">
            {doc.status === "processing"
              ? "Embeddings still processing. Search activates once ready (first upload also downloads the local embedding model)."
              : "This document failed to process. Try re-uploading."}
          </p>
        )}
        {searchError && (
          <p className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
            {searchError}
          </p>
        )}
        {hits && (
          <div className="mt-5 space-y-3">
            {hits.length === 0 ? (
              <p className="text-sm text-zinc-500">No matches.</p>
            ) : (
              hits.map((hit, idx) => (
                <article
                  key={`${hit.doc_id}-${hit.chunk_idx}`}
                  className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3"
                >
                  <header className="mb-1.5 flex items-center justify-between text-[11px] text-zinc-500">
                    <span className="font-mono text-zinc-300">
                      #{idx + 1} · {hit.filename} (chunk {hit.chunk_idx})
                    </span>
                    <span className="font-mono">score {hit.score.toFixed(3)}</span>
                  </header>
                  <p className="whitespace-pre-wrap text-sm leading-5 text-zinc-300">
                    {hit.text}
                  </p>
                </article>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StatusIcon({ status }: { status: KnowledgeStatus }) {
  if (status === "ready") {
    return <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />;
  }
  if (status === "failed") {
    return <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />;
  }
  return <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-400" />;
}

function StatusBadge({ status }: { status: KnowledgeStatus }) {
  const styles: Record<KnowledgeStatus, string> = {
    ready: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
    processing: "bg-amber-500/10 text-amber-300 border-amber-500/30",
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
        <BookOpen className="mb-3 h-6 w-6 text-zinc-600" />
        <h2 className="text-base font-medium text-zinc-200">{title}</h2>
        {body && <p className="mt-1 max-w-sm text-sm text-zinc-500">{body}</p>}
        {cta}
      </div>
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}
