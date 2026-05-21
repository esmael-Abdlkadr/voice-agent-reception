export function DataPanel({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className="overflow-hidden rounded-2xl border border-white/80 bg-white/[0.88] shadow-sm ring-1 ring-ink/[0.03] backdrop-blur">
      <div className="flex items-center justify-between gap-3 border-b border-line/80 px-5 py-4">
        <h2 className="text-[13px] font-black uppercase tracking-[0.14em] text-ink/[0.72]">{title}</h2>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}
