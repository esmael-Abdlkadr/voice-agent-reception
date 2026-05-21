import { AppShell } from "@/components/app-shell";
import { DataPanel } from "@/components/data-panel";
import { PageHeader } from "@/components/page-header";
import { StatusPill } from "@/components/status-pill";
import { api } from "@/lib/api";
import { fallbackAppointments } from "@/lib/demo";
import { visibleAppointments } from "@/lib/presentation";

export default async function AppointmentsPage() {
  const appointments = visibleAppointments(await api.appointments().catch(() => fallbackAppointments));

  return (
    <AppShell>
      <PageHeader eyebrow="Scheduling" title="Appointments booked by the assistant." description="Receptionist and outbound workflows land here with status, caller context, and operational notes." />
      <DataPanel title="Appointment board">
        {appointments.length ? (
          <div className="grid gap-3 md:grid-cols-2">
            {appointments.map((appointment) => (
              <article key={appointment.id} className="rounded-lg border border-line bg-cloud/[0.70] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="font-black">{appointment.title}</h2>
                    <p className="mt-1 text-sm text-ink/[0.62]">{appointment.contact_name}</p>
                  </div>
                  <StatusPill value={appointment.status} />
                </div>
                <p className="mt-4 text-lg font-black text-moss">{appointment.starts_at}</p>
                <p className="mt-2 text-sm text-ink/[0.65]">{appointment.notes || "Ready for confirmation."}</p>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-line bg-cloud/[0.60] px-4 py-8 text-center">
            <p className="font-black text-ink">No appointments yet</p>
            <p className="mt-2 text-sm text-ink/[0.62]">Booked appointments will appear here after customer sessions.</p>
          </div>
        )}
      </DataPanel>
    </AppShell>
  );
}
