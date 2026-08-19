"use client";

import { useState } from "react";
import { api } from "@/lib/api/client";
import { useApi } from "@/lib/api/use-api";
import { toTouchpoint } from "@/lib/api/adapters";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState, LoadingRows } from "@/components/ui/data-state";
import { TimelineItem } from "./timeline-item";
import { PatternCallout } from "./pattern-callout";

// 4471 is the seeded demo account with the deliberate breach cluster — it's
// referenced elsewhere in the demo (dashboard, ledger), so it's the default.
const DEFAULT_ACCOUNT_ID = "4471";

// A few other seeded accounts, offered as quick picks alongside free text entry.
const KNOWN_ACCOUNT_IDS = ["4471", "5820", "3392", "6104", "2277"];

function AccountSwitcher({
  accountId,
  onLookup,
}: {
  accountId: string;
  onLookup: (id: string) => void;
}) {
  const [inputValue, setInputValue] = useState(accountId);

  function submit() {
    const trimmed = inputValue.trim();
    if (trimmed) onLookup(trimmed);
  }

  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 border-b border-hairline pb-6">
      <div className="min-w-[220px]">
        <label
          htmlFor="account-lookup"
          className="font-mono text-[11px] uppercase tracking-[0.2em] text-navy-light"
        >
          Account Lookup
        </label>
        <div className="mt-2 flex gap-2">
          <input
            id="account-lookup"
            list="known-account-ids"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") submit();
            }}
            placeholder="Enter account ID…"
            className="w-44 rounded border border-hairline bg-paper px-4 py-2 font-mono text-sm text-ink-navy placeholder:text-navy-light/70 focus:border-brass-accent focus:outline-none"
          />
          <datalist id="known-account-ids">
            {KNOWN_ACCOUNT_IDS.map((id) => (
              <option key={id} value={id} />
            ))}
          </datalist>
          <Button type="button" size="sm" onClick={submit} disabled={!inputValue.trim()}>
            Look up
          </Button>
        </div>
      </div>

      <p className="font-mono text-xs text-navy-light">
        Viewing Account #{accountId}
      </p>
    </div>
  );
}

export function Timeline() {
  const [accountId, setAccountId] = useState(DEFAULT_ACCOUNT_ID);
  const { data, loading, error, retry } = useApi(() => api.timeline(accountId), [accountId]);

  return (
    <div className="rounded border border-hairline bg-card-white px-6 py-6 sm:px-8">
      <AccountSwitcher accountId={accountId} onLookup={setAccountId} />

      {loading ? (
        <LoadingRows rows={6} />
      ) : error?.code === "account_not_found" ? (
        <EmptyState message={`No account found with ID "${accountId}". Check the ID and try again.`} />
      ) : error ? (
        <ErrorState
          message={error.message}
          retryable={error.retryable}
          onRetry={retry}
          waking={error.code === "network_error"}
        />
      ) : !data || data.messages.length === 0 ? (
        <EmptyState message="No messages recorded for this account yet." />
      ) : (
        <>
          <div>
            {data.messages.map(toTouchpoint).map((touchpoint, index, arr) => (
              <TimelineItem
                key={touchpoint.id}
                touchpoint={touchpoint}
                index={index}
                isLast={index === arr.length - 1}
              />
            ))}
          </div>

          <div className="mt-2">
            <PatternCallout patterns={data.patterns} />
          </div>
        </>
      )}
    </div>
  );
}
