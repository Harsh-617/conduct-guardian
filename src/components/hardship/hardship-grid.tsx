"use client";

import { motion } from "framer-motion";
import { HeartHandshake } from "lucide-react";
import { EmptyState, ErrorState, LoadingRows } from "@/components/ui/data-state";
import { api } from "@/lib/api/client";
import { toHardshipAccount } from "@/lib/api/adapters";
import { useApi } from "@/lib/api/use-api";
import { SignalBadge } from "./signal-badge";

export function HardshipGrid() {
  const { data, loading, error, retry } = useApi(() => api.hardship(), []);

  if (loading) return <LoadingRows rows={4} />;

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

  const accounts = (data?.rows ?? []).map(toHardshipAccount);

  // No borrowers in distress is the good outcome here, not an error.
  if (accounts.length === 0) {
    return <EmptyState message="No hardship signals detected." />;
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {accounts.map((account, index) => (
        <motion.div
          key={account.id}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: index * 0.1 }}
          className="rounded border border-hairline bg-card-white px-6 py-5"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-soft-green text-stamp-green">
                <HeartHandshake className="h-4 w-4" />
              </span>
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-navy-light">
                  Account
                </p>
                <p className="font-mono text-sm font-semibold text-ink-navy">
                  {account.accountId}
                </p>
              </div>
            </div>
            <SignalBadge signal={account.signal} />
          </div>

          <p className="mt-4 text-sm italic leading-relaxed text-ink-navy">
            &ldquo;{account.quote}&rdquo;
          </p>

          <div className="mt-4 flex items-start gap-2.5 rounded border border-stamp-green/30 bg-soft-green px-4 py-3">
            <HeartHandshake className="mt-0.5 h-4 w-4 shrink-0 text-stamp-green" />
            <p className="text-xs font-medium leading-relaxed text-stamp-green">
              {account.routing}
            </p>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
