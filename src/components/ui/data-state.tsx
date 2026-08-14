"use client";

/**
 * Loading and error states, in the existing editorial aesthetic.
 *
 * PRD §9: if the Groq call fails or the backend is unreachable, the UI shows a
 * clear retry state, never a blank crash. On Render's free tier the backend
 * sleeps after ~15 minutes idle and the next request takes 30-50 seconds, so
 * "waking up" is the common case, not an error — the copy says so rather than
 * showing a red failure for something that will resolve itself.
 *
 * Uses only the tokens already defined in globals.css. No new colours.
 */

import { motion } from "framer-motion";

export function LoadingRows({ rows = 4, delay = 0 }: { rows?: number; delay?: number }) {
  return (
    <div className="flex flex-col gap-3" role="status" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0.35 }}
          animate={{ opacity: [0.35, 0.7, 0.35] }}
          transition={{
            duration: 1.6,
            repeat: Infinity,
            delay: delay + i * 0.12,
            ease: "easeInOut",
          }}
          className="h-14 rounded border border-hairline bg-card-white"
        />
      ))}
      <span className="sr-only">Loading data from the screening service</span>
    </div>
  );
}

export function LoadingCards({ cards = 4 }: { cards?: number }) {
  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      role="status"
      aria-label="Loading"
    >
      {Array.from({ length: cards }).map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0.35 }}
          animate={{ opacity: [0.35, 0.7, 0.35] }}
          transition={{ duration: 1.6, repeat: Infinity, delay: i * 0.1, ease: "easeInOut" }}
          className="h-28 rounded border border-hairline bg-card-white"
        />
      ))}
      <span className="sr-only">Loading statistics</span>
    </div>
  );
}

export function ErrorState({
  message,
  retryable,
  onRetry,
  waking,
}: {
  message: string;
  retryable: boolean;
  onRetry: () => void;
  /** True when the failure is a cold start rather than a genuine fault. */
  waking?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      role="alert"
      className={`rounded border px-6 py-5 ${
        waking
          ? "border-hairline bg-soft-brass/40"
          : "border-stamp-red/30 bg-soft-red/50"
      }`}
    >
      <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light">
        {waking ? "Service waking up" : "Could not load"}
      </p>
      <p className="mt-2 font-serif text-lg text-ink-navy">{message}</p>
      {waking && (
        <p className="mt-1 text-sm leading-relaxed text-navy-light">
          The screening service sleeps when idle. The first request can take up to a
          minute.
        </p>
      )}
      {retryable && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded border border-hairline bg-card-white px-4 py-2 font-mono text-[11px] uppercase tracking-[0.15em] text-ink-navy transition-colors hover:bg-soft-brass"
        >
          Try again
        </button>
      )}
    </motion.div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded border border-dashed border-hairline bg-card-white px-6 py-10 text-center">
      <p className="font-serif text-lg text-navy-light">{message}</p>
    </div>
  );
}
