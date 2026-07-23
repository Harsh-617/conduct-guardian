"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import { Mail, MessageCircle, MessageSquare, Phone, PhoneMissed } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Touchpoint } from "./data";

const channelIcons: Record<Touchpoint["channel"], LucideIcon> = {
  WhatsApp: MessageCircle,
  SMS: MessageSquare,
  Call: Phone,
  Email: Mail,
};

export function TimelineItem({
  touchpoint,
  index,
  isLast,
}: {
  touchpoint: Touchpoint;
  index: number;
  isLast: boolean;
}) {
  const Icon = touchpoint.missedCall
    ? PhoneMissed
    : channelIcons[touchpoint.channel];

  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, {
    once: false,
    amount: 0.5,
    margin: "0px 0px -15% 0px",
  });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 32 }}
      animate={inView ? { opacity: 1, y: 0 } : { opacity: 0, y: 32 }}
      transition={{ duration: 0.5, delay: (index % 3) * 0.1, ease: "easeOut" }}
      className="relative flex gap-5 pb-8 last:pb-0"
    >
      {!isLast && (
        <span
          className="absolute left-[15px] top-9 bottom-0 w-px bg-hairline"
          aria-hidden="true"
        />
      )}

      <span
        className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${
          touchpoint.missedCall
            ? "border-stamp-red/40 bg-soft-red text-stamp-red"
            : "border-hairline bg-card-white text-navy-light"
        }`}
      >
        <Icon className="h-4 w-4" />
      </span>

      <div className="flex-1 rounded border border-hairline bg-paper px-5 py-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="font-mono text-[10px] uppercase tracking-wide text-navy-light">
            {touchpoint.channel}
          </span>
          <span className="font-mono text-xs text-navy-light">
            {touchpoint.time}
          </span>
        </div>
        <p
          className={`mt-2 text-sm ${
            touchpoint.missedCall
              ? "italic text-navy-light"
              : "text-ink-navy"
          }`}
        >
          {touchpoint.missedCall ? (
            touchpoint.preview
          ) : (
            <>&ldquo;{touchpoint.preview}&rdquo;</>
          )}
        </p>
      </div>
    </motion.div>
  );
}
