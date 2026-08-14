"use client";

import { Fragment, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, ChevronDown, GraduationCap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingRows } from "@/components/ui/data-state";
import { api } from "@/lib/api/client";
import { formatTimestamp, toOfficer } from "@/lib/api/adapters";
import { useApi } from "@/lib/api/use-api";
import { FlagBadge } from "./flag-badge";

export function CoachingTable() {
  const [openId, setOpenId] = useState<string | null>(null);
  const { data, loading, error, retry } = useApi(() => api.coaching(), []);

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

  // Worst-conduct officers surface first, same as the flag badge's colour cue.
  const officers = (data?.rows ?? []).map(toOfficer).sort((a, b) => b.flags - a.flags);

  if (officers.length === 0) {
    return <EmptyState message="No collectors screened yet." />;
  }

  return (
    <div className="rounded border border-hairline bg-card-white px-6 py-5">
      {data && (
        <div className="mb-4 flex items-center justify-end">
          <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-navy-light">
            {data.cached ? "Cached" : "Regenerated"} · {formatTimestamp(data.generated_at)}
          </p>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-hairline">
              <th className="w-12 py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                Rank
              </th>
              <th className="py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                Officer
              </th>
              <th className="py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                Flags this month
              </th>
              <th className="w-10 py-2 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light" />
            </tr>
          </thead>
          <tbody>
            {officers.map((officer, index) => {
              const open = openId === officer.id;
              const isLast = index === officers.length - 1;

              return (
                <Fragment key={officer.id}>
                  <tr
                    onClick={() => setOpenId(open ? null : officer.id)}
                    className="cursor-pointer select-none transition-colors hover:bg-paper/60"
                    aria-expanded={open}
                  >
                    <td className="py-3 pr-4 align-middle font-mono text-xs text-navy-light">
                      {index + 1}
                    </td>
                    <td className="py-3 pr-4 align-middle font-medium text-ink-navy">
                      {officer.name}
                    </td>
                    <td className="py-3 pr-4 align-middle">
                      <FlagBadge count={officer.flags} />
                    </td>
                    <td className="py-3 align-middle">
                      <ChevronDown
                        className={`h-4 w-4 text-navy-light transition-transform duration-200 ${
                          open ? "rotate-180" : ""
                        }`}
                      />
                    </td>
                  </tr>
                  <tr className={isLast ? "" : "border-b border-hairline"}>
                    <td colSpan={4} className="p-0">
                      <AnimatePresence initial={false}>
                        {open && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.35, ease: "easeOut" }}
                            className="overflow-hidden"
                          >
                            <div className="pb-5 pt-1">
                              {officer.flags > 0 ? (
                                <div className="rounded border border-hairline bg-paper px-5 py-4">
                                  <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-navy-light">
                                    Recurring pattern
                                  </p>
                                  <p
                                    className={`mt-1.5 text-sm leading-relaxed ${
                                      officer.pattern
                                        ? "text-ink-navy"
                                        : "italic text-navy-light"
                                    }`}
                                  >
                                    {officer.pattern ??
                                      "No pattern summary available for this collector."}
                                  </p>
                                  {officer.trainingModule && (
                                    <div className="mt-4">
                                      <Button
                                        variant="secondary"
                                        size="sm"
                                        className="gap-2"
                                      >
                                        <GraduationCap className="h-3.5 w-3.5" />
                                        {officer.trainingModule}
                                      </Button>
                                    </div>
                                  )}
                                </div>
                              ) : (
                                <div className="flex items-center gap-3 rounded border border-stamp-green/30 bg-soft-green px-5 py-3.5">
                                  <CheckCircle2 className="h-4 w-4 shrink-0 text-stamp-green" />
                                  <p className="text-sm font-medium text-stamp-green">
                                    No issues this month — conduct patterns consistent
                                    with best practice.
                                  </p>
                                </div>
                              )}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </td>
                  </tr>
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
