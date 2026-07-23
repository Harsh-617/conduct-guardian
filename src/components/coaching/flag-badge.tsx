export function FlagBadge({ count }: { count: number }) {
  const styles =
    count === 0
      ? "border-stamp-green/40 bg-soft-green text-stamp-green"
      : count >= 3
        ? "border-stamp-red/40 bg-soft-red text-stamp-red"
        : "border-brass-accent/40 bg-soft-brass text-brass-accent";

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 font-mono text-xs font-semibold ${styles}`}
    >
      {count} {count === 1 ? "flag" : "flags"}
    </span>
  );
}
