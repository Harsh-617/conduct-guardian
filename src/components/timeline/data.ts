export type Channel = "WhatsApp" | "SMS" | "Call" | "Email";

export type Touchpoint = {
  id: string;
  time: string;
  channel: Channel;
  missedCall?: boolean;
  preview: string;
};

export const touchpoints: Touchpoint[] = [
  {
    id: "tp-1",
    time: "9:02am",
    channel: "WhatsApp",
    preview: "Your payment is 3 days late, please respond",
  },
  {
    id: "tp-2",
    time: "9:10am",
    channel: "Call",
    missedCall: true,
    preview: "Missed call attempt",
  },
  {
    id: "tp-3",
    time: "9:15am",
    channel: "SMS",
    preview: "Call us back immediately",
  },
  {
    id: "tp-4",
    time: "9:28am",
    channel: "Call",
    missedCall: true,
    preview: "Missed call attempt",
  },
  {
    id: "tp-5",
    time: "9:33am",
    channel: "SMS",
    preview: "This is urgent, respond now",
  },
  {
    id: "tp-6",
    time: "9:41am",
    channel: "WhatsApp",
    preview: "We will escalate this if you don't respond",
  },
  {
    id: "tp-7",
    time: "9:45am",
    channel: "Email",
    preview: "Formal Notice of Default — Account #4471",
  },
];
