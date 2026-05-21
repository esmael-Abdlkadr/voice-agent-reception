import { AppShell } from "@/components/app-shell";
import { DataPanel } from "@/components/data-panel";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";
import { fallbackContacts } from "@/lib/demo";
import { visibleContacts } from "@/lib/presentation";

export default async function ContactsPage() {
  const contacts = visibleContacts(await api.contacts().catch(() => fallbackContacts));

  return (
    <AppShell>
      <PageHeader eyebrow="Customer directory" title="Contacts ready for voice workflows." description="Manage caller records, campaign leads, and appointment context in one place." />
      <DataPanel title="Contacts">
        {contacts.length ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="text-xs uppercase tracking-[0.12em] text-ink/45">
                <tr>
                  <th className="py-2">Name</th>
                  <th>Phone</th>
                  <th>Email</th>
                  <th>Company</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {contacts.map((contact) => (
                  <tr key={contact.id}>
                    <td className="py-3 font-bold">{contact.name}</td>
                    <td>{contact.phone}</td>
                    <td>{contact.email}</td>
                    <td>{contact.company}</td>
                    <td className="capitalize">{contact.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-line bg-cloud/[0.60] px-4 py-8 text-center">
            <p className="font-black text-ink">No customer contacts yet</p>
            <p className="mt-2 text-sm text-ink/[0.62]">Contacts created from calls and campaign imports will appear here.</p>
          </div>
        )}
      </DataPanel>
    </AppShell>
  );
}
