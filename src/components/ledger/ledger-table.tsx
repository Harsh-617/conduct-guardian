"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Loader2, ShieldCheck, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api/client";
import { useApi } from "@/lib/api/use-api";
import { formatTimestamp, toLedgerRow } from "@/lib/api/adapters";
import { EmptyState, ErrorState, LoadingRows } from "@/components/ui/data-state";
import type { VerifyResponse } from "@/lib/api/types";
import { ChannelBadge } from "./channel-badge";
import { VerdictBadge } from "./verdict-badge";

const PAGE_SIZE = 25;
const ROW_DELAY = 0.05;
const CHECK_DURATION = 0.35;

type VerifyState =
  | { status: "idle" }
  | { status: "verifying" }
  | { status: "done"; result: VerifyResponse }
  | { status: "error"; error: ApiError };

export function LedgerTable() {
  const [page, setPage] = useState(1);
  const { data, loading, error, retry } = useApi(() => api.ledger(page, PAGE_SIZE), [page]);

  const [verify, setVerify] = useState<VerifyState>({ status: "idle" });
  const [runId, setRunId] = useState(0);

  const handleVerify = async () => {
    if (verify.status === "verifying") return;
    setVerify({ status: "verifying" });
    try {
      const result = await api.verifyLedger();
      setRunId((n) => n + 1);
      setVerify({ status: "done", result });
    } catch (err) {
      setVerify({
        status: "error",
        error:
          err instanceof ApiError ? err : new ApiError("Something went wrong.", "unknown", true, 0),
      });
    }
  };

  // /ledger entries now carry account/channel/snippet joined from the
  // attested message (nullable on older rows) — toLedgerRow handles the
  // nulls itself ("—" for a missing account or snippet).
  const rows =
    data?.entries.map((entry) => ({
      entry,
      row: toLedgerRow(entry),
    })) ?? [];

  const totalPages =
    data && data.page_size > 0 ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleVerify} disabled={verify.status === "verifying"} className="gap-2">
          {verify.status === "verifying" ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Verifying chain...
            </>
          ) : (
            <>
              <ShieldCheck className="h-4 w-4" />
              Verify Chain Integrity
            </>
          )}
        </Button>

        <AnimatePresence>
          {verify.status === "done" && (
            <motion.p
              key="hint"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light"
            >
              Last verified {formatTimestamp(verify.result.verified_at)}
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {verify.status === "done" && verify.result.valid && (
          <motion.div
            key="banner-success"
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="flex items-center gap-3 rounded border border-stamp-green/30 bg-soft-green px-5 py-3.5">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-stamp-green" />
              <p className="text-sm font-medium text-stamp-green">
                Chain verified — {verify.result.total} entries rehashed, {verify.result.failed}{" "}
                mismatches.
              </p>
            </div>
          </motion.div>
        )}
        {verify.status === "done" && !verify.result.valid && (
          <motion.div
            key="banner-failure"
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="flex items-center gap-3 rounded border border-stamp-red/30 bg-soft-red px-5 py-3.5">
              <XCircle className="h-5 w-5 shrink-0 text-stamp-red" />
              <p className="text-sm font-medium text-stamp-red">
                Chain integrity failure — tampering detected at entry #{verify.result.first_broken_id}.
              </p>
            </div>
          </motion.div>
        )}
        {verify.status === "error" && (
          <motion.div
            key="banner-error"
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="flex items-center gap-3 rounded border border-stamp-red/30 bg-soft-red px-5 py-3.5">
              <XCircle className="h-5 w-5 shrink-0 text-stamp-red" />
              <p className="text-sm font-medium text-stamp-red">
                Could not verify the chain: {verify.error.message}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="rounded border border-hairline bg-card-white px-6 py-5">
        {loading && <LoadingRows rows={6} />}

        {!loading && error && (
          <ErrorState
            message={error.message}
            retryable={error.retryable}
            onRetry={retry}
            waking={error.code === "network_error"}
          />
        )}

        {!loading && !error && rows.length === 0 && (
          <EmptyState message="No ledger entries recorded yet." />
        )}

        {!loading && !error && rows.length > 0 && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-hairline">
                    <th className="whitespace-nowrap py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                      Timestamp
                    </th>
                    <th className="whitespace-nowrap py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                      Account
                    </th>
                    <th className="whitespace-nowrap py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                      Channel
                    </th>
                    <th className="py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                      Snippet
                    </th>
                    <th className="whitespace-nowrap py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                      Verdict
                    </th>
                    <th className="whitespace-nowrap py-2 pr-4 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                      Rule
                    </th>
                    <th className="whitespace-nowrap py-2 font-mono text-[10px] font-medium uppercase tracking-wide text-navy-light">
                      Chain Hash
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(({ entry, row }, index) => {
                    const isBroken =
                      verify.status === "done" &&
                      !verify.result.valid &&
                      verify.result.first_broken_id === entry.id;

                    return (
                      <tr
                        key={row.id}
                        className={`border-b border-hairline last:border-0 ${
                          isBroken ? "bg-soft-red/40" : ""
                        }`}
                      >
                        <td className="whitespace-nowrap py-3 pr-4 align-top font-mono text-xs text-navy-light">
                          {row.timestamp}
                        </td>
                        <td className="whitespace-nowrap py-3 pr-4 align-top font-mono text-xs text-ink-navy">
                          {row.account}
                        </td>
                        <td className="whitespace-nowrap py-3 pr-4 align-top">
                          <ChannelBadge channel={row.channel} />
                        </td>
                        <td className="max-w-sm py-3 pr-4 align-top text-ink-navy">
                          <span className="italic">&ldquo;{row.snippet}&rdquo;</span>
                        </td>
                        <td className="whitespace-nowrap py-3 pr-4 align-top">
                          <VerdictBadge verdict={row.verdict} />
                        </td>
                        <td className="max-w-[220px] py-3 pr-4 align-top font-mono text-xs text-navy-light">
                          {row.rule ?? "—"}
                        </td>
                        <td className="whitespace-nowrap py-3 align-top">
                          <div className="flex items-center gap-2 font-mono text-xs text-navy-light">
                            <span>{row.hash}</span>
                            {isBroken && <XCircle className="h-3.5 w-3.5 text-stamp-red" />}
                            {!isBroken && verify.status === "done" && verify.result.valid && (
                              <motion.span
                                key={`check-${runId}`}
                                initial={{ opacity: 0, scale: 0.4 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{
                                  delay: index * ROW_DELAY,
                                  duration: CHECK_DURATION,
                                  ease: "easeOut",
                                }}
                              >
                                <CheckCircle2 className="h-3.5 w-3.5 text-stamp-green" />
                              </motion.span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {data && (
              <div className="mt-4 flex items-center justify-between gap-3">
                <span className="font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light">
                  Page {data.page} of {totalPages} — {data.total} entries
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="rounded border border-hairline bg-card-white px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.15em] text-ink-navy transition-colors hover:bg-soft-brass disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Prev
                  </button>
                  <button
                    type="button"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="rounded border border-hairline bg-card-white px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.15em] text-ink-navy transition-colors hover:bg-soft-brass disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
