"use client";

import { Building2, Check, ChevronsUpDown, Plus } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/components/auth-provider";

export function WorkspaceSwitcher() {
  const {
    user,
    workspaces,
    currentWorkspaceId,
    setCurrentWorkspaceId,
    openNewWorkspaceModal,
  } = useAuth();
  const canCreateWorkspace = Boolean(user?.is_superuser);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const current = workspaces.find((w) => w.id === currentWorkspaceId) ?? null;

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="group flex w-full items-center gap-2.5 rounded-lg border border-zinc-800 bg-zinc-900/60 px-2.5 py-2 text-left text-sm transition hover:border-zinc-700 hover:bg-zinc-900"
      >
        <div className="grid h-7 w-7 place-items-center rounded-md bg-zinc-800 text-zinc-300">
          <Building2 className="h-3.5 w-3.5" />
        </div>
        <div className="min-w-0 flex-1">
          {current ? (
            <>
              <div className="truncate text-[13px] font-medium text-zinc-100">
                {current.name}
              </div>
              <div className="truncate text-[10px] uppercase tracking-wider text-zinc-500">
                {current.role}
              </div>
            </>
          ) : (
            <>
              <div className="truncate text-[13px] font-medium text-zinc-300">
                No workspace
              </div>
              <div className="truncate text-[10px] uppercase tracking-wider text-zinc-500">
                {workspaces.length === 0 ? "create one" : "select"}
              </div>
            </>
          )}
        </div>
        <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-zinc-500" />
      </button>

      {open && (
        <div
          role="menu"
          className="absolute left-0 right-0 top-full z-30 mt-1.5 overflow-hidden rounded-lg border border-zinc-800 bg-zinc-900 p-1 shadow-xl shadow-black/40"
        >
          {workspaces.length === 0 ? (
            <div className="px-3 py-2 text-xs text-zinc-500">
              You have no workspaces yet.
            </div>
          ) : (
            workspaces.map((w) => {
              const active = w.id === currentWorkspaceId;
              return (
                <button
                  key={w.id}
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    setCurrentWorkspaceId(w.id);
                    setOpen(false);
                  }}
                  className={`flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition ${
                    active
                      ? "bg-zinc-800 text-zinc-100"
                      : "text-zinc-300 hover:bg-zinc-800/60"
                  }`}
                >
                  <div className="grid h-6 w-6 place-items-center rounded-md bg-zinc-800/80 text-zinc-400">
                    <Building2 className="h-3 w-3" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px] font-medium">{w.name}</div>
                    <div className="truncate text-[10px] uppercase tracking-wider text-zinc-500">
                      {w.role}
                    </div>
                  </div>
                  {active && <Check className="h-3.5 w-3.5 text-accent-400" />}
                </button>
              );
            })
          )}
          {canCreateWorkspace && (
            <>
              <div className="my-1 border-t border-zinc-800" />
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  openNewWorkspaceModal();
                }}
                className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-zinc-300 transition hover:bg-zinc-800/60"
              >
                <Plus className="h-4 w-4 text-zinc-500" />
                New workspace
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
