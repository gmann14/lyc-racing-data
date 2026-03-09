import { METHODOLOGY_LOOKUP } from "@/lib/methodology";

export default function InfoTip({
  term,
  className = "",
}: {
  term: string;
  className?: string;
}) {
  const item = METHODOLOGY_LOOKUP.get(term.toLowerCase());

  if (!item) {
    return null;
  }

  return (
    <span
      className={`inline-flex h-4 w-4 items-center justify-center rounded-full border border-border text-[10px] font-bold text-gray-400 ${className}`.trim()}
      title={`${item.term}: ${item.summary}`}
      aria-label={`${item.term}: ${item.summary}`}
    >
      i
    </span>
  );
}
