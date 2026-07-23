export type Channel = "Call" | "WhatsApp" | "SMS" | "Email";

export type Verdict = "FLAGGED" | "CLEAR";

export type LedgerRow = {
  id: string;
  timestamp: string;
  account: string;
  channel: Channel;
  snippet: string;
  verdict: Verdict;
  rule: string | null;
  hash: string;
};

export const ledgerRows: LedgerRow[] = [
  {
    id: "row-01",
    timestamp: "Jul 21, 8:14 AM",
    account: "#4471",
    channel: "SMS",
    snippet: "Pay now.",
    verdict: "FLAGGED",
    rule: "Harassment Pattern (Excessive Contact Frequency)",
    hash: "a3f9c1...e21c",
  },
  {
    id: "row-02",
    timestamp: "Jul 21, 8:02 AM",
    account: "#2038",
    channel: "WhatsApp",
    snippet: "If you don't pay by tomorrow we will send people to your house...",
    verdict: "FLAGGED",
    rule: "Threatening Language",
    hash: "7b2d4e...9a01",
  },
  {
    id: "row-03",
    timestamp: "Jul 20, 4:47 PM",
    account: "#5566",
    channel: "Call",
    snippet: "Officer: If this isn't settled by Friday, you will be arrested...",
    verdict: "FLAGGED",
    rule: "Misleading Legal Claim (False Threat of Arrest)",
    hash: "f01a88...5c3d",
  },
  {
    id: "row-04",
    timestamp: "Jul 20, 2:15 PM",
    account: "#3312",
    channel: "Call",
    snippet: "Officer: Hi, calling about your account ending 3312 — would a revised repayment plan help?",
    verdict: "CLEAR",
    rule: null,
    hash: "cd6e12...af90",
  },
  {
    id: "row-05",
    timestamp: "Jul 20, 11:33 AM",
    account: "#9027",
    channel: "SMS",
    snippet: "Hi, this is a reminder about your account. Please call us back at your convenience.",
    verdict: "CLEAR",
    rule: null,
    hash: "1e77b3...d640",
  },
  {
    id: "row-06",
    timestamp: "Jul 19, 6:52 PM",
    account: "#4471",
    channel: "WhatsApp",
    snippet: "We are calling your workplace next if you ignore this.",
    verdict: "FLAGGED",
    rule: "Third-Party Contact Threat",
    hash: "88f2a0...3b17",
  },
  {
    id: "row-07",
    timestamp: "Jul 19, 3:10 PM",
    account: "#6184",
    channel: "Email",
    snippet: "Following up on our call — happy to walk through the hardship options whenever suits you.",
    verdict: "CLEAR",
    rule: null,
    hash: "4c9d71...0e2a",
  },
  {
    id: "row-08",
    timestamp: "Jul 19, 9:05 AM",
    account: "#7745",
    channel: "Call",
    snippet: "Officer: No pressure at all — take your time, and call us back once you've had a chance to review.",
    verdict: "CLEAR",
    rule: null,
    hash: "e5a03f...7712",
  },
  {
    id: "row-09",
    timestamp: "Jul 18, 5:28 PM",
    account: "#2038",
    channel: "SMS",
    snippet: "Answer your phone.",
    verdict: "FLAGGED",
    rule: "Harassment Pattern (Excessive Contact Frequency)",
    hash: "0b4f6d...c885",
  },
  {
    id: "row-10",
    timestamp: "Jul 18, 1:00 PM",
    account: "#5089",
    channel: "WhatsApp",
    snippet: "Thanks for the update — I've noted the new payment date on the account.",
    verdict: "CLEAR",
    rule: null,
    hash: "9a1c2e...4f08",
  },
];
