import type { HardshipSignal } from "./data";

export function SignalBadge({ signal }: { signal: HardshipSignal }) {
  return (
    <span className="inline-flex shrink-0 items-center rounded-full border border-stamp-green/40 bg-soft-green px-2.5 py-1 font-mono text-[10px] uppercase tracking-wide text-stamp-green">
      {signal}
    </span>
  );
}
