"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ledgerRows } from "./data";
import { ChannelBadge } from "./channel-badge";
import { VerdictBadge } from "./verdict-badge";

const ROW_DELAY = 0.1;
const CHECK_DURATION = 0.35;
const BANNER_BUFFER = 0.35;

type VerifyStatus = "idle" | "verifying" | "verified";

export function LedgerTable() {
  const [status, setStatus] = useState<VerifyStatus>("idle");
  const [runId, setRunId] = useState(0);

  const handleVerify = () => {
    if (status === "verifying") return;

    setStatus("verifying");
    setRunId((id) => id + 1);

    const totalSeconds =
      (ledgerRows.length - 1) * ROW_DELAY + CHECK_DURATION + BANNER_BUFFER;

    setTimeout(() => setStatus("verified"), totalSeconds * 1000);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button
          onClick={handleVerify}
          disabled={status === "verifying"}
          className="gap-2"
        >
          {status === "verifying" ? (
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
          {status === "verified" && (
            <motion.p
              key="hint"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light"
            >
              Last verified just now
            </motion.p>
          )}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {status === "verified" && (
          <motion.div
            key="banner"
            initial={{ opacity: 0, y: -8, height: 0 }}
            animate={{ opacity: 1, y: 0, height: "auto" }}
            exit={{ opacity: 0, y: -8, height: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <div className="flex items-center gap-3 rounded border border-stamp-green/30 bg-soft-green px-5 py-3.5">
              <CheckCircle2 className="h-5 w-5 shrink-0 text-stamp-green" />
              <p className="text-sm font-medium text-stamp-green">
                Chain verified — all 10 entries intact, no tampering detected.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="rounded border border-hairline bg-card-white px-6 py-5">
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
              {ledgerRows.map((row, index) => (
                <tr key={row.id} className="border-b border-hairline last:border-0">
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
                      {status !== "idle" && (
                        <motion.span
                          key={runId}
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
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
