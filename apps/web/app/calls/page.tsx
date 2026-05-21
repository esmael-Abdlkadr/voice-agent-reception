import { AppShell } from "@/components/app-shell";
import { DataPanel } from "@/components/data-panel";
import { PageHeader } from "@/components/page-header";
import { StatusPill } from "@/components/status-pill";
import { api } from "@/lib/api";
import { fallbackCalls } from "@/lib/demo";
import { visibleCalls } from "@/lib/presentation";

export default async function CallsPage() {
  const calls = visibleCalls(await api.calls().catch(() => fallbackCalls));

  return (
    <AppShell>
      <PageHeader eyebrow="Call intelligence" title="Transcripts, summaries, and outcomes." description="Every conversation is captured with caller context, assistant replies, business summary, and next-step outcome." />
      <DataPanel title="Call history">
        {calls.length ? (
          <div className="grid gap-3">
            {calls.map((call) => (
              <article key={call.id} className="rounded-lg border border-line bg-cloud/[0.70] p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="font-black text-ink">{call.contact_name}</h2>
                    <p className="text-sm capitalize text-ink/60">
                      {call.provider === "twilio" ? "Twilio phone session" : `${call.direction} call`}
                      {call.caller_number ? ` from ${call.caller_number}` : ""}
                    </p>
                  </div>
                  <StatusPill value={call.outcome} />
                </div>
                {call.provider === "twilio" ? (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold text-ink/[0.58]">
                    <span className="rounded-full bg-white px-2.5 py-1">CallSid: {call.external_call_id}</span>
                    <span className="rounded-full bg-white px-2.5 py-1">Status: {call.provider_status || call.status}</span>
                    <span className="rounded-full bg-white px-2.5 py-1">Duration: {call.duration_seconds ?? 0}s</span>
                  </div>
                ) : null}
                <p className="mt-3 text-sm leading-6 text-ink/[0.72]">{call.summary || "Awaiting transcript review."}</p>
                <div className="mt-3 space-y-2">
                  {call.messages.map((message) => (
                    <p key={message.id} className="rounded-md bg-white px-3 py-2 text-sm text-ink/75">
                      <strong className="capitalize">{message.role}:</strong> {message.content}
                    </p>
                  ))}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-line bg-cloud/[0.60] px-4 py-8 text-center">
            <p className="font-black text-ink">No customer calls yet</p>
            <p className="mt-2 text-sm text-ink/[0.62]">Completed sessions will appear here with transcripts and summaries.</p>
          </div>
        )}
      </DataPanel>
    </AppShell>
  );
}
