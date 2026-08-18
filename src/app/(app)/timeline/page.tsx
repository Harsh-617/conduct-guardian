import { Timeline } from "@/components/timeline/timeline";

export default function TimelinePage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-navy-light">
          Case Timeline
        </p>
        <h1 className="mt-1 font-serif text-3xl font-semibold text-ink-navy">
          Cross-Channel Contact Timeline
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-navy-light">
          Every touchpoint across every channel, merged into one record.
        </p>
      </div>

      <Timeline />
    </div>
  );
}
