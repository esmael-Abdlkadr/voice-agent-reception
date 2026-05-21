"use client";

import { FormEvent, useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { LockKeyhole, RadioTower, ShieldCheck } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

export default function LoginPage() {
  const router = useRouter();
  const { login, status } = useAuth();
  const [email, setEmail] = useState("admin@voiceagent.local");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (status === "authenticated") router.replace("/");
  }, [router, status]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    startTransition(async () => {
      try {
        await login(email, password);
        router.replace("/");
      } catch {
        setError("Login failed. Check the email, password, and API server.");
      }
    });
  }

  return (
    <main className="grid min-h-screen grid-cols-1 bg-cloud lg:grid-cols-[0.95fr_1.05fr]">
      <section className="hidden border-r border-line bg-ink px-10 py-10 text-white lg:flex lg:flex-col lg:justify-between">
        <div>
          <div className="inline-flex items-center gap-3 rounded-md bg-white/10 px-3 py-2">
            <RadioTower className="h-5 w-5 text-coral" />
            <span className="text-sm font-black">VoiceAgentOS</span>
          </div>
          <h1 className="mt-10 max-w-xl text-5xl font-black leading-tight">Secure console for AI calls, campaigns, and knowledge.</h1>
        </div>
        <div className="grid gap-3 text-sm text-white/70">
          <p>Groq-backed assistant responses</p>
          <p>Role-based access for platform teams</p>
          <p>Call logs, appointments, transcripts, and analytics</p>
        </div>
      </section>

      <section className="flex items-center justify-center px-4 py-8">
        <form onSubmit={submit} className="w-full max-w-md rounded-lg border border-line bg-white p-5 shadow-soft sm:p-6">
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.14em] text-moss">Authenticated access</p>
              <h2 className="mt-2 text-2xl font-black text-ink">Sign in</h2>
            </div>
            <div className="grid h-11 w-11 place-items-center rounded-md bg-mint text-ink">
              <ShieldCheck className="h-5 w-5" />
            </div>
          </div>

          <label className="block text-sm font-bold text-ink" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="focus-ring mt-2 w-full rounded-md border border-line bg-cloud px-3 py-3 text-sm text-ink"
            autoComplete="username"
          />

          <label className="mt-4 block text-sm font-bold text-ink" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="focus-ring mt-2 w-full rounded-md border border-line bg-cloud px-3 py-3 text-sm text-ink"
            autoComplete="current-password"
          />

          {error ? <p className="mt-4 rounded-md border border-coral/[0.40] bg-coral/[0.10] px-3 py-2 text-sm font-bold text-coral">{error}</p> : null}

          <button
            type="submit"
            disabled={isPending}
            className="focus-ring mt-5 flex w-full items-center justify-center gap-2 rounded-md bg-ink px-4 py-3 text-sm font-black text-white transition hover:bg-moss disabled:opacity-60"
          >
            <LockKeyhole className="h-4 w-4" />
            {isPending ? "Signing in..." : "Sign in to platform"}
          </button>

          <div className="mt-5 rounded-md border border-line bg-cloud px-3 py-3 text-xs leading-5 text-ink/[0.68]">
            Seeded admin: <strong>admin@voiceagent.local</strong> / <strong>admin123</strong>
          </div>
        </form>
      </section>
    </main>
  );
}
