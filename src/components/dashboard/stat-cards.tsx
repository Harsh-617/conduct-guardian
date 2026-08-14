"use client";

import { motion } from "framer-motion";
import { AnimatedNumber } from "./animated-number";
import { ErrorState, LoadingCards } from "@/components/ui/data-state";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/api/use-api";
import type { DashboardStats } from "@/lib/api/types";

function buildStats(stats: DashboardStats) {
  return [
    { label: "Messages Screened", value: stats.total_screened, decimals: 0, suffix: "" },
    { label: "Violations Caught", value: stats.total_violations, decimals: 0, suffix: "" },
    { label: "Active Accounts", value: stats.active_accounts, decimals: 0, suffix: "" },
    { label: "Open Hardship Cases", value: stats.open_hardship_cases, decimals: 0, suffix: "" },
  ];
}

export function StatCards({ sectionDelay = 0 }: { sectionDelay?: number }) {
  const { data, loading, error, retry } = useApi(() => api.dashboardStats());

  if (loading) return <LoadingCards cards={4} />;

  if (error) {
    return (
      <ErrorState
        message={error.message}
        retryable={error.retryable}
        onRetry={retry}
        waking={error.code === "network_error"}
      />
    );
  }

  if (!data) return null;

  const stats = buildStats(data);

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, index) => {
        const delay = sectionDelay + index * 0.1;
        return (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay }}
            className="rounded border border-hairline bg-card-white px-6 py-5"
          >
            <p className="font-serif text-4xl font-semibold text-brass-accent">
              <AnimatedNumber
                value={stat.value}
                decimals={stat.decimals}
                suffix={stat.suffix}
                delay={delay}
                duration={1}
              />
            </p>
            <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light">
              {stat.label}
            </p>
          </motion.div>
        );
      })}
    </div>
  );
}
