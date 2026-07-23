import type { Verdict } from "./data";

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const flagged = verdict === "FLAGGED";

  return (
    <span
      className={`inline-flex select-none items-center justify-center rounded border-2 px-2 py-0.5 font-serif text-[11px] font-black uppercase tracking-[0.08em] ${
        flagged
          ? "border-stamp-red text-stamp-red"
          : "border-stamp-green text-stamp-green"
      }`}
      style={{
        transform: flagged ? "rotate(-3deg)" : "rotate(2deg)",
        boxShadow: flagged
          ? "0 0 0 1px rgba(158,43,37,0.12) inset"
          : "0 0 0 1px rgba(46,94,78,0.12) inset",
      }}
    >
      {verdict}
    </span>
  );
}
