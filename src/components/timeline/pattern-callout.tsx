"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { TriangleAlert } from "lucide-react";

export function PatternCallout() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, {
    once: false,
    amount: 0.3,
    margin: "0px 0px -5% 0px",
  });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 28, scale: 0.96 }}
      animate={
        inView ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0, y: 28, scale: 0.96 }
      }
      transition={{ duration: 0.55, delay: 0.35, ease: "easeOut" }}
      className="ml-0 rounded border-2 border-stamp-red bg-soft-red px-6 py-5 sm:ml-[52px]"
    >
      <div className="flex items-start gap-3">
        <TriangleAlert className="mt-0.5 h-5 w-5 shrink-0 text-stamp-red" />
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-stamp-red">
            Pattern Detected
          </p>
          <p className="mt-1.5 text-base font-semibold leading-relaxed text-stamp-red">
            7 contact attempts across 4 channels within 43 minutes —
            harassment pattern.
          </p>
          <p className="mt-2 text-sm leading-relaxed text-ink-navy">
            This would be invisible if each channel were reviewed
            separately.
          </p>
        </div>
      </div>
    </motion.div>
  );
}
