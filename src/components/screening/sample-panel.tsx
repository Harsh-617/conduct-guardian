"use client";

import { MessageCircle, MessageSquare, Phone } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { samples } from "./data";
import type { SampleMessage } from "./data";

const channelIcons: Record<SampleMessage["channel"], LucideIcon> = {
  Call: Phone,
  WhatsApp: MessageCircle,
  SMS: MessageSquare,
};

export function SamplePanel({
  selectedId,
  onSelect,
}: {
  selectedId: string | null;
  onSelect: (sample: SampleMessage) => void;
}) {
  return (
    <div className="rounded border border-hairline bg-card-white px-5 py-5">
      <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light">
        Sample Messages
      </p>
      <h2 className="mt-1 font-serif text-lg font-semibold text-ink-navy">
        Load a Scenario
      </h2>

      <div className="mt-4 flex flex-col gap-2">
        {samples.map((sample) => {
          const Icon = channelIcons[sample.channel];
          const active = sample.id === selectedId;
          return (
            <button
              key={sample.id}
              type="button"
              onClick={() => onSelect(sample)}
              className={`flex flex-col gap-1.5 rounded border px-3.5 py-3 text-left transition-colors ${
                active
                  ? "border-brass-accent bg-soft-brass"
                  : "border-hairline bg-paper hover:border-brass-accent/50 hover:bg-soft-brass/40"
              }`}
            >
              <span className="flex items-center gap-2">
                <Icon
                  className={`h-3.5 w-3.5 shrink-0 ${
                    active ? "text-brass-accent" : "text-navy-light"
                  }`}
                />
                <span className="font-mono text-[10px] uppercase tracking-wide text-navy-light">
                  {sample.channel}
                </span>
              </span>
              <span className="text-sm font-medium text-ink-navy">
                {sample.label}
              </span>
            </button>
          );
        })}
      </div>

      <p className="mt-4 border-t border-hairline pt-3 text-xs leading-relaxed text-navy-light">
        Select a scenario to load it into the preview, or write your own
        message below.
      </p>
    </div>
  );
}
