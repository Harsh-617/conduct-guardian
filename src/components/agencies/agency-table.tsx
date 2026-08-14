"use client";

import { motion } from "framer-motion";
import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import { EmptyState, ErrorState, LoadingRows } from "@/components/ui/data-state";
import { api } from "@/lib/api/client";
import { toAgency } from "@/lib/api/adapters";
import { useApi } from "@/lib/api/use-api";
import type { Trend } from "./data";

function scoreColor(score: number) {
  if (score < 70) return "text-stamp-red";
  if (score < 85) return "text-brass-accent";
  return "text-stamp-green";
}

// The backend keeps no score history (compliance_score is computed fresh on
// every read), so `trend` is always "stable" — see toAgency(). This renders
// the neutral state for every row rather than hiding the column, which keeps
// the layout intact and doesn't pretend we know a direction we don't.
function TrendIcon({ trend }: { trend: Trend }) {
  if (trend === "improving") {
    return (
      <span className="inline-flex items-center gap-1.5 font-mono text-xs uppercase tracking-wide text-stamp-green">
        <TrendingUp className="h-3.5 w-3.5" />
        Improving
      </span>
    );
  }
  if (trend === "declining") {
    return (
      <span className="inline-flex items-center gap-1.5 font-mono text-xs uppercase tracking-wide text-stamp-red">
        <TrendingDown className="h-3.5 w-3.5" />
        Declining
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-xs uppercase tracking-wide text-navy-light">
      <Minus className="h-3.5 w-3.5" />
      Stable
    </span>
  );
}

export function AgencyTable() {
  const { data, loading, error, retry } = useApi(() => api.agencies(), []);

  if (loading) {
    return (
      <div className="rounded border border-hairline bg-card-white px-6 py-5">
        <LoadingRows rows={5} />
      </div>
    );
  }

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

  // Worst compliance first, same ordering the mock data used.
  const agencies = (data?.rows ?? []).map(toAgency).sort((a, b) => a.score - b.score);

  if (agencies.length === 0) {
    return <EmptyState message="No agencies on file yet." />;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="overflow-x-auto rounded border border-hairline bg-card-white"
    >
      <table className="w-full min-w-[640px] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-hairline">
            <th className="py-3 pl-6 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
              Agency Name
            </th>
            <th className="whitespace-nowrap py-3 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
              Compliance Score
            </th>
            <th className="whitespace-nowrap py-3 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
              Flags This Month
            </th>
            <th className="whitespace-nowrap py-3 pr-6 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
              Trend
            </th>
          </tr>
        </thead>
        <tbody>
          {agencies.map((agency, index) => {
            const needsAttention = agency.score < 70;
            return (
              <motion.tr
                key={agency.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: index * 0.08 }}
                className={`border-b border-hairline last:border-0 ${
                  needsAttention
                    ? "border-l-4 border-l-stamp-red bg-soft-red/40"
                    : ""
                }`}
              >
                <td className="py-4 pl-6 pr-4 align-middle font-medium text-ink-navy">
                  {agency.name}
                </td>
                <td className="py-4 pr-4 align-middle">
                  <span
                    className={`font-serif text-2xl font-semibold ${scoreColor(
                      agency.score
                    )}`}
                  >
                    {agency.score}
                  </span>
                </td>
                <td className="py-4 pr-4 align-middle font-mono text-sm text-ink-navy">
                  {agency.flags}
                </td>
                <td className="py-4 pr-6 align-middle">
                  <TrendIcon trend={agency.trend} />
                </td>
              </motion.tr>
            );
          })}
        </tbody>
      </table>
    </motion.div>
  );
}
