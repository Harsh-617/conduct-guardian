"use client";

import { motion } from "framer-motion";
import type { Verdict } from "./data";

export function VerdictStamp({ verdict }: { verdict: Verdict }) {
  const flagged = verdict === "FLAGGED";

  return (
    <motion.div
      key={verdict}
      initial={{ opacity: 0, scale: 2.4, rotate: flagged ? -14 : 10 }}
      animate={{ opacity: 1, scale: 1, rotate: flagged ? -8 : 6 }}
      transition={{ type: "spring", stiffness: 320, damping: 14, mass: 0.9 }}
      className={`inline-flex select-none items-center justify-center rounded-md border-[5px] px-6 py-2.5 font-serif text-3xl font-black uppercase tracking-[0.12em] sm:text-4xl ${
        flagged
          ? "border-stamp-red text-stamp-red"
          : "border-stamp-green text-stamp-green"
      }`}
      style={{
        boxShadow: flagged
          ? "0 0 0 2px rgba(158,43,37,0.15) inset"
          : "0 0 0 2px rgba(46,94,78,0.15) inset",
      }}
    >
      {verdict}
    </motion.div>
  );
}
