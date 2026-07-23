"use client";

import { motion } from "framer-motion";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const data = [
  { date: "Jul 10", count: 2 },
  { date: "Jul 11", count: 1 },
  { date: "Jul 12", count: 3 },
  { date: "Jul 13", count: 0 },
  { date: "Jul 14", count: 4 },
  { date: "Jul 15", count: 1 },
  { date: "Jul 16", count: 2 },
  { date: "Jul 17", count: 1 },
  { date: "Jul 18", count: 2 },
  { date: "Jul 19", count: 0 },
  { date: "Jul 20", count: 3 },
  { date: "Jul 21", count: 1 },
  { date: "Jul 22", count: 2 },
  { date: "Jul 23", count: 3 },
];

const axisTickStyle = {
  fontFamily: "var(--font-ibm-plex-mono)",
  fontSize: 11,
  fill: "#3B4356",
};

export function ViolationsChart({ delay = 0 }: { delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className="rounded border border-hairline bg-card-white px-6 py-5"
    >
      <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light">
        Last 14 Days
      </p>
      <h2 className="mt-1 font-serif text-xl font-semibold text-ink-navy">
        Violations Caught
      </h2>
      <div className="mt-4 h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 24, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="violationsFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#9E2B25" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#9E2B25" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#D8D3C2" vertical={false} />
            <XAxis
              dataKey="date"
              tick={axisTickStyle}
              axisLine={{ stroke: "#D8D3C2" }}
              tickLine={false}
              padding={{ left: 12, right: 12 }}
              interval={0}
            />
            <YAxis
              allowDecimals={false}
              tick={axisTickStyle}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip
              contentStyle={{
                background: "#FBFAF5",
                border: "1px solid #D8D3C2",
                borderRadius: 4,
                fontFamily: "var(--font-ibm-plex-mono)",
                fontSize: 12,
                color: "#1C2333",
              }}
              labelStyle={{ color: "#1C2333", fontWeight: 600 }}
              cursor={{ stroke: "#D8D3C2" }}
            />
            <Area
              type="monotone"
              dataKey="count"
              name="Violations"
              stroke="#9E2B25"
              strokeWidth={2}
              fill="url(#violationsFill)"
              dot={{ r: 3, fill: "#9E2B25", strokeWidth: 0 }}
              activeDot={{ r: 5 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
