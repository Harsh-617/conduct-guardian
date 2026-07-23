export type HardshipSignal =
  | "Job Loss"
  | "Health Crisis"
  | "Bereavement"
  | "Financial Distress";

export type HardshipAccount = {
  id: string;
  accountId: string;
  quote: string;
  signal: HardshipSignal;
  routing: string;
};

export const hardshipAccounts: HardshipAccount[] = [
  {
    id: "hardship-01",
    accountId: "#7734",
    quote: "I just lost my job last week, I don't know what I'm going to do.",
    signal: "Job Loss",
    routing:
      "Routed to specialist — standard escalation paused, restructuring conversation scheduled.",
  },
  {
    id: "hardship-02",
    accountId: "#2915",
    quote:
      "I've been in and out of the hospital, I can barely think about this right now.",
    signal: "Health Crisis",
    routing:
      "Routed to specialist — standard escalation paused, restructuring conversation scheduled.",
  },
  {
    id: "hardship-03",
    accountId: "#6048",
    quote:
      "My husband passed away last month, I haven't been able to deal with any of this.",
    signal: "Bereavement",
    routing:
      "Routed to specialist — standard escalation paused, restructuring conversation scheduled.",
  },
  {
    id: "hardship-04",
    accountId: "#3382",
    quote:
      "I've had to choose between paying this and buying groceries this week.",
    signal: "Financial Distress",
    routing:
      "Routed to specialist — standard escalation paused, restructuring conversation scheduled.",
  },
];
