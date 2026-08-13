"use client";

/**
 * Renders TimelineResponse.patterns (only `triggered: true` flags).
 *
 * Two visibly different treatments, by `is_published_limit`:
 *  - true  -> a real Bank Negara limit. Strongest existing treatment
 *             (stamp-red / soft-red), same weight the original mock used.
 *  - false -> our own internal heuristic, not law. Visibly weaker treatment
 *             (brass / soft-brass, dashed hairline) and the eyebrow says
 *             "Internal Heuristic" so it is never mistaken for a regulatory
 *             breach — the API's `label` text already contains the word too.
 */

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { TriangleAlert } from "lucide-react";
import type { PatternFlag } from "@/lib/api/types";

function PatternCard({ pattern, index }: { pattern: PatternFlag; index: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, {
    once: false,
    amount: 0.3,
    margin: "0px 0px -5% 0px",
  });

  const isRegulatory = pattern.is_published_limit;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 28, scale: 0.96 }}
      animate={
        inView ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0, y: 28, scale: 0.96 }
      }
      transition={{ duration: 0.55, delay: 0.35 + index * 0.1, ease: "easeOut" }}
      className={
        isRegulatory
          ? "ml-0 rounded border-2 border-stamp-red bg-soft-red px-6 py-5 sm:ml-[52px]"
          : "ml-0 rounded border border-dashed border-brass-accent/60 bg-soft-brass px-6 py-5 sm:ml-[52px]"
      }
    >
      <div className="flex items-start gap-3">
        <TriangleAlert
          className={`mt-0.5 h-5 w-5 shrink-0 ${
            isRegulatory ? "text-stamp-red" : "text-brass-accent"
          }`}
        />
        <div>
          <p
            className={`font-mono text-[10px] uppercase tracking-[0.15em] ${
              isRegulatory ? "text-stamp-red" : "text-brass-accent"
            }`}
          >
            {isRegulatory ? "Pattern Detected — Regulatory Limit" : "Pattern Detected — Internal Heuristic"}
          </p>
          <p
            className={`mt-1.5 text-base leading-relaxed ${
              isRegulatory ? "font-semibold text-stamp-red" : "font-medium text-navy-light"
            }`}
          >
            {pattern.label}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-ink-navy">{pattern.detail}</p>
        </div>
      </div>
    </motion.div>
  );
}

export function PatternCallout({ patterns }: { patterns: PatternFlag[] }) {
  const triggered = patterns.filter((p) => p.triggered);

  if (triggered.length === 0) return null;

  return (
    <div className="flex flex-col gap-3">
      {triggered.map((pattern, index) => (
        <PatternCard key={pattern.rule} pattern={pattern} index={index} />
      ))}
    </div>
  );
}
