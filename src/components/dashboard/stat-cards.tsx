"use client";

import { motion } from "framer-motion";
import { AnimatedNumber } from "./animated-number";

const stats = [
  { label: "Messages Screened Today", value: 247, decimals: 0, suffix: "" },
  { label: "Violations Caught This Week", value: 12, decimals: 0, suffix: "" },
  { label: "Agencies Monitored", value: 6, decimals: 0, suffix: "" },
  { label: "Avg. Response Time", value: 1.2, decimals: 1, suffix: "s" },
];

export function StatCards({ sectionDelay = 0 }: { sectionDelay?: number }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat, index) => {
        const delay = sectionDelay + index * 0.1;
        return (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay }}
            className="rounded border border-hairline bg-card-white px-6 py-5"
          >
            <p className="font-serif text-4xl font-semibold text-brass-accent">
              <AnimatedNumber
                value={stat.value}
                decimals={stat.decimals}
                suffix={stat.suffix}
                delay={delay}
                duration={1}
              />
            </p>
            <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light">
              {stat.label}
            </p>
          </motion.div>
        );
      })}
    </div>
  );
}
