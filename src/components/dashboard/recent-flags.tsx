"use client";

import { motion } from "framer-motion";
import { Mail, MessageCircle, MessageSquare, Phone } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { EmptyState, ErrorState, LoadingRows } from "@/components/ui/data-state";
import { api } from "@/lib/api/client";
import { toLedgerRow } from "@/lib/api/adapters";
import { useApi } from "@/lib/api/use-api";
import type { Channel } from "@/components/ledger/data";

const channelIcons: Record<Channel, LucideIcon> = {
  WhatsApp: MessageCircle,
  SMS: MessageSquare,
  Call: Phone,
  Email: Mail,
};

function ChannelBadge({ channel }: { channel: Channel }) {
  const Icon = channelIcons[channel];
  return (
    <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-hairline bg-paper px-2.5 py-1 font-mono text-[10px] uppercase tracking-wide text-navy-light">
      <Icon className="h-3 w-3" />
      {channel}
    </span>
  );
}

function RulePill({ rule }: { rule: string }) {
  return (
    <span className="inline-flex shrink-0 items-center rounded-full bg-soft-brass px-3 py-1 font-mono text-[10px] uppercase tracking-wide text-brass-accent">
      {rule}
    </span>
  );
}

// Rows with no rule are a CLEAR verdict, not missing data — styled after the
// CLEAR state used elsewhere (ledger/verdict-badge.tsx, hardship/signal-badge.tsx).
function ClearPill() {
  return (
    <span className="inline-flex shrink-0 items-center rounded-full border border-stamp-green/40 bg-soft-green px-3 py-1 font-mono text-[10px] uppercase tracking-wide text-stamp-green">
      Clear
    </span>
  );
}

export function RecentFlags({ delay = 0 }: { delay?: number }) {
  // violations_only: this panel is "Recent Flags", so a clean entry has no
  // business in it. Filtered server-side rather than in the browser — the last
  // five entries being clean would otherwise leave the panel empty while real
  // violations sat one row below the cutoff.
  const { data, loading, error, retry } = useApi(() => api.ledger(1, 5, true));
  const rows = (data?.entries ?? []).map(toLedgerRow);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="rounded border border-hairline bg-card-white px-6 py-5"
    >
      <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light">
        Live Screening
      </p>
      <h2 className="mt-1 font-serif text-xl font-semibold text-ink-navy">
        Recent Flags
      </h2>

      <div className="mt-4">
        {loading ? (
          <LoadingRows rows={5} />
        ) : error ? (
          <ErrorState
            message={error.message}
            retryable={error.retryable}
            onRetry={retry}
            waking={error.code === "network_error"}
          />
        ) : rows.length === 0 ? (
          <EmptyState message="No screening activity yet." />
        ) : (
          <ul className="divide-y divide-hairline">
            {rows.map((row) => (
              <li
                key={row.id}
                className="flex flex-col gap-3 py-4 first:pt-2 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex flex-1 flex-wrap items-start gap-3 sm:flex-nowrap sm:items-center">
                  <span className="w-32 shrink-0 font-mono text-xs text-navy-light">
                    {row.timestamp}
                  </span>
                  <ChannelBadge channel={row.channel} />
                  <p className="text-sm text-ink-navy">
                    <span className="italic">&ldquo;{row.snippet}&rdquo;</span>{" "}
                    <span className="font-mono text-xs text-navy-light">
                      — {row.account}
                    </span>
                  </p>
                </div>
                {row.rule ? <RulePill rule={row.rule} /> : <ClearPill />}
              </li>
            ))}
          </ul>
        )}
      </div>
    </motion.div>
  );
}
