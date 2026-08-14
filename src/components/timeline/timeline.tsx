"use client";

import { api } from "@/lib/api/client";
import { useApi } from "@/lib/api/use-api";
import { toTouchpoint } from "@/lib/api/adapters";
import { EmptyState, ErrorState, LoadingRows } from "@/components/ui/data-state";
import { TimelineItem } from "./timeline-item";
import { PatternCallout } from "./pattern-callout";

// Account 4471 is the seeded demo account with the deliberate breach cluster.
const ACCOUNT_ID = "4471";

export function Timeline() {
  const { data, loading, error, retry } = useApi(() => api.timeline(ACCOUNT_ID), []);

  if (loading) {
    return (
      <div className="rounded border border-hairline bg-card-white px-6 py-6 sm:px-8">
        <LoadingRows rows={6} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded border border-hairline bg-card-white px-6 py-6 sm:px-8">
        <ErrorState
          message={error.message}
          retryable={error.retryable}
          onRetry={retry}
          waking={error.code === "network_error"}
        />
      </div>
    );
  }

  if (!data || data.messages.length === 0) {
    return (
      <div className="rounded border border-hairline bg-card-white px-6 py-6 sm:px-8">
        <EmptyState message="No messages recorded for this account yet." />
      </div>
    );
  }

  const touchpoints = data.messages.map(toTouchpoint);

  return (
    <div className="rounded border border-hairline bg-card-white px-6 py-6 sm:px-8">
      <div>
        {touchpoints.map((touchpoint, index) => (
          <TimelineItem
            key={touchpoint.id}
            touchpoint={touchpoint}
            index={index}
            isLast={index === touchpoints.length - 1}
          />
        ))}
      </div>

      <div className="mt-2">
        <PatternCallout patterns={data.patterns} />
      </div>
    </div>
  );
}
