import Link from "next/link";
import { Activity, ArrowUpRight, BrainCircuit, CalendarCheck, Headphones, Megaphone, PhoneCall, RadioTower } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { DataPanel } from "@/components/data-panel";
import { MetricCard } from "@/components/metric-card";
import { StatusPill } from "@/components/status-pill";
import { api } from "@/lib/api";
import { fallbackAppointments, fallbackCalls, fallbackCampaigns, fallbackOverview } from "@/lib/demo";
import { outcomeLabel, visibleAppointments, visibleCalls, visibleCampaigns } from "@/lib/presentation";

export default async function DashboardPage() {
  const [overview, calls, appointments, campaigns] = await Promise.all([
    api.overview().catch(() => fallbackOverview),
    api.calls().catch(() => fallbackCalls),
    api.appointments().catch(() => fallbackAppointments),
    api.campaigns().catch(() => fallbackCampaigns),
  ]);
  const customerCalls = visibleCalls(calls);
  const customerAppointments = visibleAppointments(appointments);
  const customerCampaigns = visibleCampaigns(campaigns);
  const completedCalls = customerCalls.filter((call) => call.status === "completed");
  const recentCalls = completedCalls.slice(-5).reverse();
  const outcomeMix = completedCalls.reduce<Record<string, number>>((outcomes, call) => {
    outcomes[call.outcome] = (outcomes[call.outcome] ?? 0) + 1;
    return outcomes;
  }, {});
  const maxOutcomeCount = Math.max(1, ...Object.values(outcomeMix));
  const conversionRate = completedCalls.length ? Math.round((customerAppointments.length / completedCalls.length) * 100) : 0;
  const knowledgeReplies = Math.min(overview.rag_questions_answered, completedCalls.length);
  const latestAppointment = customerAppointments.at(-1);

  return (
    <AppShell>
      <section className="relative overflow-hidden rounded-[2rem] border border-white/70 bg-ink px-5 py-5 text-white shadow-soft sm:px-7 lg:px-8">
        <div className="absolute -right-20 -top-24 h-72 w-72 rounded-full bg-coral/[0.30] blur-3xl" />
        <div className="absolute bottom-0 left-1/2 h-48 w-96 -translate-x-1/2 rounded-full bg-mint/[0.15] blur-3xl" />
        <div className="relative grid gap-6 lg:grid-cols-[1fr_360px] lg:items-end">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/[0.12] bg-white/[0.08] px-3 py-1.5 text-xs font-black uppercase tracking-[0.16em] text-mint">
              <RadioTower className="h-4 w-4" />
              Command center
            </div>
            <h1 className="mt-5 max-w-4xl text-4xl font-black leading-[0.95] tracking-tight sm:text-5xl xl:text-6xl">
              AI voice operations for BrightCare Dental.
            </h1>
            <p className="mt-5 max-w-3xl text-base leading-7 text-white/[0.68]">
              Manage live receptionist sessions, campaign follow-ups, appointment bookings, grounded knowledge answers, and call outcomes from one secure workspace.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <Link href="/playground" className="focus-ring inline-flex items-center justify-center gap-2 rounded-2xl bg-coral px-4 py-3 text-sm font-black text-white shadow-lg shadow-coral/20 transition hover:-translate-y-0.5">
                <Headphones className="h-4 w-4" />
                Start live agent
              </Link>
              <Link href="/campaigns" className="focus-ring inline-flex items-center justify-center gap-2 rounded-2xl border border-white/[0.12] bg-white/[0.08] px-4 py-3 text-sm font-black text-white transition hover:-translate-y-0.5 hover:bg-white/[0.12]">
                <Megaphone className="h-4 w-4" />
                Review campaigns
              </Link>
            </div>
          </div>
          <div className="rounded-[1.5rem] border border-white/[0.12] bg-white/[0.08] p-4 backdrop-blur">
            <p className="text-xs font-black uppercase tracking-[0.16em] text-white/[0.52]">Operations pulse</p>
            <div className="mt-4 grid gap-3">
              <div className="flex items-center justify-between rounded-2xl bg-black/[0.20] px-4 py-3">
                <span className="text-sm text-white/[0.68]">Completion rate</span>
                <span className="text-2xl font-black">{conversionRate}%</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-black/[0.20] px-4 py-3">
                <span className="text-sm text-white/[0.68]">Latest booking</span>
                <span className="max-w-44 truncate text-right text-sm font-black">{latestAppointment?.starts_at ?? "No bookings yet"}</span>
              </div>
              <div className="flex items-center justify-between rounded-2xl bg-black/[0.20] px-4 py-3">
                <span className="text-sm text-white/[0.68]">AI provider</span>
                <span className="text-sm font-black">Groq</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={PhoneCall} label="Calls handled" value={completedCalls.length} detail="Completed customer conversations" />
        <MetricCard icon={CalendarCheck} label="Appointments" value={customerAppointments.length} detail="Booked and ready for follow-up" />
        <MetricCard icon={BrainCircuit} label="Knowledge replies" value={knowledgeReplies} detail="Answers grounded in business content" />
        <MetricCard icon={Megaphone} label="Campaigns" value={customerCampaigns.length} detail="Outbound workflows configured" />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <DataPanel title="Recent customer outcomes">
          {recentCalls.length ? (
            <div className="space-y-3">
              {recentCalls.map((call) => (
                <div key={call.id} className="group flex flex-col gap-3 rounded-2xl border border-line/80 bg-cloud/[0.70] p-4 transition hover:border-moss/[0.20] hover:bg-white sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex min-w-0 items-start gap-3">
                    <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-ink text-sm font-black text-white">
                      {call.contact_name.slice(0, 1)}
                    </div>
                    <div className="min-w-0">
                      <p className="font-black text-ink">{call.contact_name}</p>
                      <p className="mt-1 line-clamp-2 text-sm leading-5 text-ink/[0.62]">{call.summary}</p>
                    </div>
                  </div>
                  <StatusPill value={call.outcome} />
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-line bg-cloud/[0.60] px-4 py-10 text-center">
              <Activity className="mx-auto h-8 w-8 text-moss" />
              <p className="mt-3 font-black text-ink">No completed customer calls yet</p>
              <p className="mt-2 text-sm text-ink/[0.62]">Completed live agent sessions and campaign calls will appear here.</p>
            </div>
          )}
        </DataPanel>

        <div className="grid gap-5">
          <DataPanel title="Outcome mix">
            {Object.keys(outcomeMix).length ? (
              <div className="space-y-4">
                {Object.entries(outcomeMix).map(([outcome, count]) => (
                  <div key={outcome}>
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="capitalize text-ink/70">{outcomeLabel(outcome)}</span>
                      <span className="font-black">{count}</span>
                    </div>
                    <div className="h-2.5 rounded-full bg-line">
                      <div className="h-2.5 rounded-full bg-gradient-to-r from-moss to-coral" style={{ width: `${Math.max(14, (count / maxOutcomeCount) * 100)}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-line bg-cloud/[0.60] px-4 py-8 text-center text-sm text-ink/[0.62]">No completed outcomes yet.</div>
            )}
          </DataPanel>

          <section className="overflow-hidden rounded-2xl border border-moss/[0.15] bg-mint/[0.70] p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-moss/[0.70]">Next best action</p>
                <h2 className="mt-2 text-xl font-black text-ink">Review booked appointments</h2>
                <p className="mt-2 text-sm leading-6 text-ink/[0.62]">Confirm the latest assistant bookings and prepare the next customer follow-up.</p>
              </div>
              <ArrowUpRight className="h-5 w-5 text-moss" />
            </div>
            <Link href="/appointments" className="focus-ring mt-5 inline-flex items-center justify-center rounded-2xl bg-ink px-4 py-3 text-sm font-black text-white transition hover:bg-moss">
              Open appointments
            </Link>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
