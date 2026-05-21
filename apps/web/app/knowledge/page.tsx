import { Search } from "lucide-react";
import { AppShell } from "@/components/app-shell";
import { DataPanel } from "@/components/data-panel";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";
import { fallbackKnowledge } from "@/lib/demo";
import { visibleKnowledgeDocuments } from "@/lib/presentation";

export default async function KnowledgePage() {
  const docs = visibleKnowledgeDocuments(await api.knowledge().catch(() => fallbackKnowledge));

  return (
    <AppShell>
      <PageHeader eyebrow="Knowledge base" title="Business answers grounded in approved content." description="The assistant can answer pricing, hours, first-visit, and emergency questions from BrightCare Dental resources." />
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <DataPanel title="Knowledge documents">
          {docs.length ? (
            <div className="grid gap-3">
              {docs.map((doc) => (
                <article key={doc.id} className="rounded-lg border border-line bg-cloud/[0.70] p-4">
                  <h2 className="font-black">{doc.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-ink/[0.68]">{doc.content}</p>
                  <p className="mt-3 text-xs font-bold uppercase tracking-[0.14em] text-moss">{doc.source_name}</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-line bg-cloud/[0.60] px-4 py-8 text-center">
              <p className="font-black text-ink">No knowledge documents yet</p>
              <p className="mt-2 text-sm text-ink/[0.62]">Approved FAQs and service details will appear here.</p>
            </div>
          )}
        </DataPanel>
        <aside className="rounded-xl border border-line bg-ink p-4 text-white shadow-soft">
          <Search className="h-8 w-8 text-coral" />
          <h2 className="mt-3 text-xl font-black">Suggested questions</h2>
          <div className="mt-4 space-y-2 text-sm text-white/75">
            <p>How much is whitening?</p>
            <p>Do you handle emergencies?</p>
            <p>What should I bring to my first visit?</p>
          </div>
        </aside>
      </div>
    </AppShell>
  );
}
