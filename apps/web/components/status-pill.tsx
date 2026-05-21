import { outcomeLabel } from "@/lib/presentation";

export function StatusPill({ value }: { value: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-moss/[0.15] bg-mint/[0.85] px-3 py-1 text-xs font-black capitalize text-moss shadow-sm">
      {outcomeLabel(value)}
    </span>
  );
}
