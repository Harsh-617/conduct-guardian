import { CoachingTable } from "@/components/coaching/coaching-table";

export default function CoachingPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-navy-light">
          Conduct Review · This Month
        </p>
        <h1 className="mt-1 font-serif text-3xl font-semibold text-ink-navy">
          Collector Coaching
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-navy-light">
          Turning recurring flags into targeted retraining, not blanket
          policing.
        </p>
      </div>

      <CoachingTable />
    </div>
  );
}
