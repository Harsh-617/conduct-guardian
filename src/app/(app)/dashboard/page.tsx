import { RecentFlags } from "@/components/dashboard/recent-flags";
import { StatCards } from "@/components/dashboard/stat-cards";
import { ViolationsChart } from "@/components/dashboard/violations-chart";

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-navy-light">
          Thursday, July 23, 2026
        </p>
        <h1 className="mt-1 font-serif text-3xl font-semibold text-ink-navy">
          Dashboard
        </h1>
      </div>

      <StatCards sectionDelay={0.1} />
      <ViolationsChart delay={0.3} />
      <RecentFlags delay={0.45} />
    </div>
  );
}
