"use client";

import { FormEvent, useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

export default function LoginPage() {
  const router = useRouter();
  const { login, status } = useAuth();
  const [email, setEmail] = useState("admin@voiceops.dev");
  const [password, setPassword] = useState("voiceops-dev");
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
        setError("Login failed. Check the email, password, and that the API is running.");
      }
    });
  }

  return (
    <main className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      <HeroPane />

      <section className="relative flex items-center justify-center bg-zinc-950 px-6 py-10">
        <div className="w-full max-w-sm">
          <div className="mb-12 flex items-center gap-2 lg:hidden">
            <Mark />
            <span className="text-base font-medium tracking-tight">VoiceOps</span>
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">
            Sign in
          </h1>
          <p className="mt-1.5 text-sm text-zinc-400">
            Use your operator credentials.
          </p>

          <form onSubmit={submit} className="mt-9 space-y-5">
            <div>
              <label
                className="block text-[11px] font-medium uppercase tracking-wider text-zinc-500"
                htmlFor="email"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
                className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-accent-400/60 focus:shadow-glow"
              />
            </div>

            <div>
              <label
                className="block text-[11px] font-medium uppercase tracking-wider text-zinc-500"
                htmlFor="password"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                className="mt-2 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-100 outline-none transition placeholder:text-zinc-600 focus:border-accent-400/60 focus:shadow-glow"
              />
            </div>

            {error && (
              <p className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={isPending}
              className="group flex w-full items-center justify-center gap-1.5 rounded-lg bg-accent-400 px-4 py-2.5 text-sm font-medium text-zinc-950 transition hover:bg-accent-300 disabled:opacity-60"
            >
              {isPending ? "Signing in..." : "Continue"}
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
            </button>
          </form>

          <div className="mt-10 border-t border-zinc-900 pt-5">
            <p className="font-mono text-[11px] text-zinc-600">
              dev seed
            </p>
            <p className="mt-1 font-mono text-[11px] text-zinc-500">
              admin@voiceops.dev · voiceops-dev
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

function HeroPane() {
  // Bars used for the decorative waveform. Heights chosen to read like
  // a voice waveform rather than a chart.
  const bars = [
    14, 28, 18, 42, 22, 56, 34, 70, 28, 48, 16, 36, 22, 60, 38, 52, 24, 44, 18,
    32, 14, 22,
  ];

  return (
    <section className="relative hidden overflow-hidden border-r border-zinc-900 bg-zinc-950 lg:flex lg:flex-col lg:justify-between lg:px-12 lg:py-12">
      {/* Ambient layered glows — soft, off-center, not a head-on radial */}
      <div
        aria-hidden
        className="pointer-events-none absolute -left-32 top-0 h-[36rem] w-[36rem] rounded-full bg-accent-500/[0.08] blur-[110px]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute bottom-0 right-0 h-[28rem] w-[28rem] rounded-full bg-accent-400/[0.05] blur-[110px]"
      />

      {/* Logo */}
      <div className="relative flex items-center gap-2.5">
        <Mark />
        <span className="text-base font-medium tracking-tight">VoiceOps</span>
      </div>

      {/* Center pitch */}
      <div className="relative max-w-xl">
        <p className="mb-4 inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.18em] text-accent-400">
          <span className="h-1.5 w-1.5 rounded-full bg-accent-400 animate-pulse-glow" />
          Voice-AI Ops Console
        </p>
        <h2 className="text-4xl font-semibold leading-[1.1] tracking-tight text-zinc-100 lg:text-5xl">
          Every customer call,
          <br />
          <span className="text-zinc-500">answered, captured, searchable.</span>
        </h2>
        <p className="mt-5 max-w-md text-sm leading-relaxed text-zinc-400">
          Run AI voice agents for your clients. Watch live calls, configure
          personas, ground answers in their knowledge base, review every
          transcript — from one console.
        </p>
      </div>

      {/* Waveform decoration */}
      <div className="relative">
        <div className="mb-3 flex items-end gap-1 text-zinc-700">
          {bars.map((h, i) => (
            <span
              key={i}
              className="w-1 rounded-full bg-current"
              style={{
                height: `${h}px`,
                background:
                  i % 5 === 0
                    ? "rgba(34, 211, 238, 0.5)"
                    : "rgb(63, 63, 70)",
              }}
            />
          ))}
        </div>
        <div className="flex items-center gap-6 font-mono text-[11px] text-zinc-600">
          <span>Groq · LLM</span>
          <span>Deepgram · STT</span>
          <span>Cartesia · TTS</span>
          <span>LiveKit · transport</span>
        </div>
      </div>
    </section>
  );
}

function Mark() {
  return (
    <div className="grid h-8 w-8 place-items-center rounded-md bg-gradient-to-br from-accent-400 to-accent-600 text-sm font-bold text-zinc-950">
      V
    </div>
  );
}
