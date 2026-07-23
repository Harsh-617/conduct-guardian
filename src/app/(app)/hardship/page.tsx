import { HardshipGrid } from "@/components/hardship/hardship-grid";

export default function HardshipPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-navy-light">
          Customer Protection
        </p>
        <h1 className="mt-1 font-serif text-3xl font-semibold text-ink-navy">
          Hardship Queue
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-navy-light">
          The same system that catches collector misconduct also protects
          customers showing genuine hardship.
        </p>
      </div>

      <HardshipGrid />
    </div>
  );
}
