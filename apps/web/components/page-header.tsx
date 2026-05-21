export function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="mb-4 rounded-xl border border-line bg-white/[0.78] px-4 py-4 shadow-sm backdrop-blur">
      <p className="text-xs font-black uppercase tracking-[0.16em] text-moss">{eyebrow}</p>
      <div className="mt-2">
        <h1 className="max-w-4xl text-2xl font-black leading-tight text-ink sm:text-3xl">{title}</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-ink/[0.66]">{description}</p>
      </div>
    </header>
  );
}
