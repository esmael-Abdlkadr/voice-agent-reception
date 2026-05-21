import type { LucideIcon } from "lucide-react";

export function MetricCard({ label, value, detail, icon: Icon }: { label: string; value: string | number; detail: string; icon?: LucideIcon }) {
  return (
    <section className="group relative overflow-hidden rounded-2xl border border-white/80 bg-white/90 p-4 shadow-sm ring-1 ring-ink/[0.03] transition hover:-translate-y-0.5 hover:shadow-soft">
      <div className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-coral via-moss to-mint opacity-80" />
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-black uppercase tracking-[0.16em] text-ink/45">{label}</p>
        {Icon ? (
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-ink text-white shadow-sm transition group-hover:bg-moss">
            <Icon className="h-4 w-4" />
          </div>
        ) : null}
      </div>
      <p className="mt-4 text-4xl font-black tracking-tight text-ink">{value}</p>
      <p className="mt-1 text-sm leading-5 text-ink/[0.58]">{detail}</p>
    </section>
  );
}
