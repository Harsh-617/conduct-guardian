export type Channel = "Call" | "WhatsApp" | "SMS";

export type Verdict = "FLAGGED" | "CLEAR";

export type Highlight = {
  before: string;
  match: string;
  after: string;
};

export type CannedResult = {
  verdict: Verdict;
  rule: string | null;
  rewrite: string | null;
  highlight: Highlight | null;
};

export type SampleMessage = {
  id: string;
  label: string;
  channel: Channel;
  account: string;
  text: string;
  result: CannedResult;
};

export type LogEntry = {
  id: string;
  timestamp: string;
  snippet: string;
  verdict: Verdict;
  rule: string | null;
};

export const samples: SampleMessage[] = [
  {
    id: "clean-call",
    label: "Clean call",
    channel: "Call",
    account: "Account #4521",
    text: "Officer: Hi, this is Ravi from the collections team, calling about your account ending 4521. I understand things have been tight — would it help to talk through a revised repayment plan for the next few months?",
    result: {
      verdict: "CLEAR",
      rule: null,
      rewrite: null,
      highlight: null,
    },
  },
  {
    id: "implied-threat",
    label: "Implied threat",
    channel: "WhatsApp",
    account: "Account #2038",
    text: "If you don't pay by tomorrow we will send people to your house and you will regret it. This is your last warning.",
    result: {
      verdict: "FLAGGED",
      rule: "Threatening Language",
      rewrite:
        "If payment isn't received by tomorrow, we may need to escalate this account for further review. I'd like to help you avoid that — can we look at a payment plan that works for you today?",
      highlight: {
        before: "If you don't pay by tomorrow ",
        match: "we will send people to your house and you will regret it",
        after: ". This is your last warning.",
      },
    },
  },
  {
    id: "misleading-legal-claim",
    label: "Misleading legal claim",
    channel: "Call",
    account: "Account #5566",
    text: "Officer: If this isn't settled by Friday, you will be arrested and it will go on your criminal record permanently, so I suggest you pay right now.",
    result: {
      verdict: "FLAGGED",
      rule: "Misleading Legal Claim (False Threat of Arrest)",
      rewrite:
        "Officer: If this isn't settled by Friday, the account may be escalated for further collections review. I'd recommend resolving it now — would a short-term payment plan help?",
      highlight: {
        before: "Officer: If this isn't settled by Friday, ",
        match:
          "you will be arrested and it will go on your criminal record permanently",
        after: ", so I suggest you pay right now.",
      },
    },
  },
  {
    id: "harassment-pattern",
    label: "Harassment pattern",
    channel: "SMS",
    account: "Account #4471",
    text: "SMS 1 (7:02am): Pay now.\nSMS 2 (7:14am): Pay now or else.\nSMS 3 (7:20am): We are calling your workplace next if you ignore this.\nSMS 4 (7:41am): Answer your phone.",
    result: {
      verdict: "FLAGGED",
      rule: "Harassment Pattern (Excessive Contact Frequency)",
      rewrite:
        'Consolidate outreach into a single, courteous message per day, e.g.: "Hi, this is a reminder about your account. Please call us back at your convenience to discuss payment options." Avoid repeat contact within a 24-hour window without a response, and never reference contacting a third party like an employer.',
      highlight: {
        before:
          "SMS 1 (7:02am): Pay now.\nSMS 2 (7:14am): Pay now or else.\n",
        match: "SMS 3 (7:20am): We are calling your workplace next if you ignore this.",
        after: "\nSMS 4 (7:41am): Answer your phone.",
      },
    },
  },
];
