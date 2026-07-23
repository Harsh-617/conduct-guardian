"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { LogEntry } from "./data";

export function EvidenceLog({ entries }: { entries: LogEntry[] }) {
  return (
    <div className="rounded border border-hairline bg-card-white px-6 py-5">
      <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light">
        Audit Trail
      </p>
      <h2 className="mt-1 font-serif text-xl font-semibold text-ink-navy">
        Evidence Log
      </h2>

      {entries.length === 0 ? (
        <p className="mt-6 text-sm text-navy-light">
          Run a compliance review above to start logging results here.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-hairline">
                <th className="whitespace-nowrap py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                  Timestamp
                </th>
                <th className="py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                  Snippet
                </th>
                <th className="whitespace-nowrap py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                  Verdict
                </th>
                <th className="whitespace-nowrap py-2 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                  Rule
                </th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence initial={false}>
                {entries.map((entry) => (
                  <motion.tr
                    key={entry.id}
                    initial={{ opacity: 0, backgroundColor: "rgba(161,127,45,0.18)" }}
                    animate={{ opacity: 1, backgroundColor: "rgba(161,127,45,0)" }}
                    transition={{ duration: 0.9 }}
                    className="border-b border-hairline last:border-0"
                  >
                    <td className="whitespace-nowrap py-3 pr-4 align-top font-mono text-xs text-navy-light">
                      {entry.timestamp}
                    </td>
                    <td className="max-w-md py-3 pr-4 align-top text-ink-navy">
                      <span className="italic">&ldquo;{entry.snippet}&rdquo;</span>
                    </td>
                    <td className="whitespace-nowrap py-3 pr-4 align-top">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wide ${
                          entry.verdict === "FLAGGED"
                            ? "bg-soft-red text-stamp-red"
                            : "bg-soft-green text-stamp-green"
                        }`}
                      >
                        {entry.verdict}
                      </span>
                    </td>
                    <td className="py-3 align-top font-mono text-xs text-navy-light">
                      {entry.rule ?? "—"}
                    </td>
                  </motion.tr>
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
