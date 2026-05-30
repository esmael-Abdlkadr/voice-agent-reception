"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import {
  BookOpen,
  Bot,
  CalendarDays,
  LogOut,
  Mic,
  Phone,
  PhoneCall,
  Radio,
  Settings,
  Wrench,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { NewWorkspaceModal } from "@/components/new-workspace-modal";
import { WorkspaceSwitcher } from "@/components/workspace-switcher";
import type { WorkspaceRole } from "@/lib/types";

const navItems: {
  href: string;
  label: string;
  icon: typeof Radio;
  minRole: WorkspaceRole;
  disabled?: boolean;
}[] = [
  { href: "/", label: "Live", icon: Radio, minRole: "admin" },
  { href: "/call", label: "Test Call", icon: Mic, minRole: "viewer" },
  { href: "/calls", label: "Calls", icon: PhoneCall, minRole: "viewer" },
  { href: "/reservations", label: "Reservations", icon: CalendarDays, minRole: "viewer" },
  { href: "/agent", label: "Agent", icon: Bot, minRole: "admin" },
  { href: "/numbers", label: "Numbers", icon: Phone, minRole: "admin" },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen, minRole: "admin" },
  { href: "/tools", label: "Tools", icon: Wrench, minRole: "admin" },
  { href: "/settings", label: "Settings", icon: Settings, minRole: "owner", disabled: true },
];

export function AppShell({
  children,
  requires,
}: {
  children: React.ReactNode;
  /** Minimum workspace role required to view this page. */
  requires?: WorkspaceRole;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const {
    status,
    user,
    logout,
    refresh,
    setCurrentWorkspaceId,
    hasAccess,
    newWorkspaceModalOpen,
    closeNewWorkspaceModal,
  } = useAuth();

  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [router, status]);

  const firstAllowed = navItems.find((i) => !i.disabled && hasAccess(i.minRole))?.href;
  const blocked = requires !== undefined && !hasAccess(requires);
  useEffect(() => {
    if (status === "authenticated" && blocked && firstAllowed && pathname === "/") {
      router.replace(firstAllowed);
    }
  }, [status, blocked, firstAllowed, pathname, router]);

  if (status !== "authenticated") {
    return (
      <div className="grid min-h-screen place-items-center bg-zinc-950 px-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 px-5 py-4 text-sm text-zinc-300">
          Checking your session...
        </div>
      </div>
    );
  }

  const visibleNav = navItems.filter((i) => hasAccess(i.minRole));
  const accessDenied = requires !== undefined && !hasAccess(requires);

  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
      <aside className="flex w-60 shrink-0 flex-col border-r border-zinc-800/80 bg-zinc-950">
        <div className="px-5 py-5">
          <div className="mb-5 flex items-center gap-2">
            <div className="grid h-7 w-7 place-items-center rounded-md bg-gradient-to-br from-accent-400 to-accent-600 text-xs font-bold text-zinc-950">
              V
            </div>
            <div className="text-sm font-medium tracking-tight text-zinc-100">
              VoiceOps
            </div>
          </div>
          <WorkspaceSwitcher />
        </div>

        <nav className="flex-1 overflow-y-auto px-3">
          <div className="mb-2 px-2 text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-500">
            Workspace
          </div>
          {visibleNav.map((item) => {
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname === item.href || pathname.startsWith(`${item.href}/`);
            const ItemEl = item.disabled ? "div" : Link;
            return (
              <ItemEl
                key={item.href}
                {...(item.disabled ? {} : { href: item.href })}
                className={`group mb-0.5 flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition ${
                  item.disabled
                    ? "cursor-not-allowed text-zinc-600"
                    : active
                      ? "bg-zinc-900 text-zinc-100"
                      : "text-zinc-400 hover:bg-zinc-900/60 hover:text-zinc-200"
                }`}
              >
                <item.icon
                  className={`h-4 w-4 ${
                    active && !item.disabled ? "text-accent-400" : ""
                  }`}
                />
                <span>{item.label}</span>
                {item.disabled && (
                  <span className="ml-auto rounded bg-zinc-900 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wider text-zinc-500">
                    soon
                  </span>
                )}
              </ItemEl>
            );
          })}
        </nav>

        <div className="border-t border-zinc-800/80 px-3 py-3">
          <div className="mb-2 flex items-center gap-2.5 rounded-md px-2 py-1.5">
            <div className="grid h-7 w-7 place-items-center rounded-full bg-zinc-800 text-xs font-medium text-zinc-300">
              {(user?.name ?? "?").slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-xs font-medium text-zinc-200">
                {user?.name}
              </div>
              <div className="truncate text-[11px] text-zinc-500">
                {user?.email}
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              logout();
              router.replace("/login");
            }}
            className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-zinc-400 transition hover:bg-zinc-900 hover:text-zinc-200"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1 bg-zinc-950">
        {accessDenied ? (
          <div className="mx-auto max-w-2xl px-10 pb-16 pt-10">
            <div className="grid place-items-center rounded-2xl border border-zinc-800 bg-zinc-900/30 py-20 text-center">
              <div className="mb-3 grid h-11 w-11 place-items-center rounded-full border border-zinc-800 bg-zinc-900 text-zinc-500">
                <Settings className="h-5 w-5" />
              </div>
              <h2 className="text-base font-medium text-zinc-200">
                You don't have access to this page
              </h2>
              <p className="mt-1 max-w-sm text-sm text-zinc-500">
                This is a configuration area for workspace admins and owners.
                Your role here is read-only.
              </p>
              <Link
                href="/"
                className="mt-5 rounded-lg bg-accent-400 px-3.5 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300"
              >
                Back to Live
              </Link>
            </div>
          </div>
        ) : (
          children
        )}
      </main>

      <NewWorkspaceModal
        open={newWorkspaceModalOpen}
        onClose={closeNewWorkspaceModal}
        onCreated={async (id) => {
          closeNewWorkspaceModal();
          await refresh();
          setCurrentWorkspaceId(id);
        }}
      />
    </div>
  );
}
