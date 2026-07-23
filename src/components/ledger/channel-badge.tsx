import { Mail, MessageCircle, MessageSquare, Phone } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Channel } from "./data";

const channelIcons: Record<Channel, LucideIcon> = {
  WhatsApp: MessageCircle,
  SMS: MessageSquare,
  Call: Phone,
  Email: Mail,
};

export function ChannelBadge({ channel }: { channel: Channel }) {
  const Icon = channelIcons[channel];

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-hairline bg-paper px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wide text-navy-light">
      <Icon className="h-3 w-3" />
      {channel}
    </span>
  );
}
