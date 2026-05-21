import { Megaphone } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { DataPanel } from "@/components/data-panel";
import { PageHeader } from "@/components/page-header";
import { StatusPill } from "@/components/status-pill";
import { api } from "@/lib/api";
import { fallbackCampaigns } from "@/lib/demo";
import { visibleCampaigns } from "@/lib/presentation";

export default async function CampaignsPage() {
  const campaigns = visibleCampaigns(await api.campaigns().catch(() => fallbackCampaigns));

  return (
    <AppShell>
      <PageHeader eyebrow="Outbound campaigns" title="Lead workflows with qualification and booking." description="Import contacts, start a campaign workflow, review outcomes, and move qualified leads into appointments." />
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <DataPanel title="Campaigns">
          {campaigns.length ? (
            <div className="grid gap-3">
              {campaigns.map((campaign) => (
                <article key={campaign.id} className="rounded-lg border border-line bg-cloud/[0.70] p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h2 className="font-black">{campaign.name}</h2>
                      <p className="mt-1 text-sm capitalize text-ink/[0.62]">{campaign.mode} campaign</p>
                    </div>
                    <StatusPill value={campaign.status} />
                  </div>
                  <p className="mt-3 text-sm leading-6 text-ink/[0.65]">CSV intake, lead qualification, callback routing, and appointment booking are tracked against this workflow.</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-line bg-cloud/[0.60] px-4 py-8 text-center">
              <p className="font-black text-ink">No campaigns yet</p>
              <p className="mt-2 text-sm text-ink/[0.62]">Create or import a campaign to begin outbound lead follow-up.</p>
            </div>
          )}
        </DataPanel>
        <aside className="rounded-xl border border-line bg-white/[0.08]4 p-4 shadow-sm">
          <Megaphone className="h-8 w-8 text-coral" />
          <h2 className="mt-3 text-xl font-black">Lead intake</h2>
          <p className="mt-2 text-sm leading-6 text-ink/[0.65]">Upload CSV contacts, run qualification flows, track callback requests, and review appointment conversion from the campaign board.</p>
        </aside>
      </div>
    </AppShell>
  );
}
