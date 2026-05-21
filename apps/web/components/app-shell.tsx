"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BarChart3, BookOpen, CalendarDays, Headphones, LayoutDashboard, LogOut, Megaphone, Settings, ShieldCheck, Sparkles, Users } from "lucide-react";
import { useEffect } from "react";
import { useAuth } from "@/components/auth-provider";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/playground", label: "Live Agent", icon: Headphones },
  { href: "/calls", label: "Calls", icon: BarChart3 },
  { href: "/appointments", label: "Appointments", icon: CalendarDays },
  { href: "/contacts", label: "Contacts", icon: Users },
  { href: "/campaigns", label: "Campaigns", icon: Megaphone },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings },
];

function roleLabel(role?: string) {
  return (role ?? "").replaceAll("_", " ") || "signed in";
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status, user, logout } = useAuth();

  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [router, status]);

  if (status !== "authenticated") {
    return (
      <div className="grid min-h-screen place-items-center px-4">
        <div className="rounded-md border border-line bg-white px-5 py-4 text-sm font-bold text-ink shadow-soft">Checking secure session...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-3 py-3 sm:px-5 lg:px-6">
      <div className="mx-auto flex max-w-[1720px] flex-col gap-5 lg:flex-row">
        <aside className="overflow-hidden rounded-[1.7rem] border border-white/[0.10] bg-ink p-3 text-white shadow-soft lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)] lg:w-72">
          <div className="relative mb-4 overflow-hidden rounded-[1.35rem] border border-white/[0.10] bg-white/[0.06] px-3 py-4">
            <div className="absolute -right-10 -top-10 h-28 w-28 rounded-full bg-coral/[0.25] blur-2xl" />
            <div className="relative flex items-center gap-3">
              <div className="grid h-11 w-11 place-items-center rounded-2xl bg-coral font-black shadow-lg shadow-coral/20">V</div>
              <div className="min-w-0">
                <p className="text-base font-black leading-tight">VoiceAgentOS</p>
                <p className="truncate text-xs font-medium text-white/[0.62]">Operations console</p>
              </div>
            </div>
            <div className="relative mt-4 flex items-center gap-3 rounded-2xl bg-black/[0.20] px-3 py-3 ring-1 ring-white/[0.10]">
              <div className="grid h-9 w-9 place-items-center rounded-xl bg-mint/[0.15] text-mint">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-black">{user?.name}</p>
                <p className="truncate text-xs capitalize text-white/[0.56]">{roleLabel(user?.role)}</p>
              </div>
            </div>
          </div>
          <nav className="grid grid-cols-2 gap-2 lg:grid-cols-1">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`focus-ring flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-bold transition ${
                    active ? "bg-mint text-ink shadow-sm" : "text-white/[0.68] hover:bg-white/[0.10] hover:text-white"
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  <span className="truncate">{item.label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="mt-4 rounded-2xl border border-white/[0.10] bg-white/[0.06] p-3">
            <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-mint">
              <Sparkles className="h-4 w-4" />
              Ready
            </div>
            <p className="mt-2 text-sm leading-5 text-white/[0.62]">AI calls, knowledge answers, campaign outcomes, and appointments are connected.</p>
          </div>
          <button
            type="button"
            onClick={() => {
              logout();
              router.replace("/login");
            }}
            className="focus-ring mt-4 flex w-full items-center justify-center gap-2 rounded-2xl border border-white/[0.10] bg-white/[0.06] px-3 py-3 text-sm font-black text-white transition hover:bg-white/[0.12]"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </aside>
        <main className="min-w-0 flex-1 pb-8">{children}</main>
      </div>
    </div>
  );
}
