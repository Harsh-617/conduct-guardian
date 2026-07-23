"use client";

import { motion } from "framer-motion";
import { Mail, MessageCircle, MessageSquare, Phone } from "lucide-react";
import type { LucideIcon } from "lucide-react";

type Channel = "WhatsApp" | "SMS" | "Call" | "Email";

const channelIcons: Record<Channel, LucideIcon> = {
  WhatsApp: MessageCircle,
  SMS: MessageSquare,
  Call: Phone,
  Email: Mail,
};

const flags: {
  time: string;
  channel: Channel;
  account: string;
  snippet: string;
  rule: string;
}[] = [
  {
    time: "9:41 AM",
    channel: "WhatsApp",
    account: "Account #2038",
    snippet: "You need to pay now or things will get a lot worse for you.",
    rule: "Threatening Language",
  },
  {
    time: "8:15 AM",
    channel: "SMS",
    account: "Account #5566",
    snippet: "This is your final legal notice before criminal charges are filed.",
    rule: "Misleading Legal Claim",
  },
  {
    time: "Yesterday, 6:52 PM",
    channel: "Call",
    account: "Account #4471",
    snippet: "I've called you twelve times today, you can't keep avoiding this.",
    rule: "Harassment Pattern",
  },
  {
    time: "Yesterday, 3:20 PM",
    channel: "Email",
    account: "Account #3190",
    snippet: "Loan agreement summary — required disclosure statement not attached.",
    rule: "Missing Disclosure",
  },
  {
    time: "Yesterday, 11:03 AM",
    channel: "SMS",
    account: "Account #6642",
    snippet: "We will contact your employer if you don't respond by Friday.",
    rule: "Threatening Language",
  },
];

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

export function RecentFlags({ delay = 0 }: { delay?: number }) {
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

      <ul className="mt-4 divide-y divide-hairline">
        {flags.map((flag) => (
          <li
            key={`${flag.time}-${flag.account}`}
            className="flex flex-col gap-3 py-4 first:pt-2 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex flex-1 items-start gap-3 sm:items-center">
              <span className="w-32 shrink-0 font-mono text-xs text-navy-light">
                {flag.time}
              </span>
              <ChannelBadge channel={flag.channel} />
              <p className="text-sm text-ink-navy">
                <span className="italic">&ldquo;{flag.snippet}&rdquo;</span>{" "}
                <span className="font-mono text-xs text-navy-light">
                  — {flag.account}
                </span>
              </p>
            </div>
            <RulePill rule={flag.rule} />
          </li>
        ))}
      </ul>
    </motion.div>
  );
}
