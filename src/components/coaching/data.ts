export type Officer = {
  id: string;
  name: string;
  flags: number;
  pattern: string | null;
  trainingModule: string | null;
  note: string | null;
};

export const officers: Officer[] = [
  {
    id: "ravi",
    name: "Ravi",
    flags: 4,
    pattern:
      "3 of 4 flags involve implying legal consequences before day 30, often using similar phrasing near payment deadlines.",
    trainingModule: "De-escalation language for early-stage collections",
    note: null,
  },
  {
    id: "aisha",
    name: "Aisha",
    flags: 3,
    pattern:
      "2 of 3 flags involve contacting the same borrower more than twice within a single day, exceeding permitted contact frequency.",
    trainingModule: "Contact frequency and cooling-off protocols",
    note: null,
  },
  {
    id: "daniel",
    name: "Daniel",
    flags: 2,
    pattern:
      "Both flags involve disclosing account details to a third party who answered the borrower's phone.",
    trainingModule: "Third-party disclosure boundaries",
    note: null,
  },
  {
    id: "priya",
    name: "Priya",
    flags: 1,
    pattern:
      "Single flag for a pressuring tone during a call with a borrower who had already disclosed financial hardship.",
    trainingModule: "Recognizing and responding to hardship signals",
    note: null,
  },
  {
    id: "wei-ling",
    name: "Wei Ling",
    flags: 1,
    pattern:
      "Single flag for a follow-up SMS sent outside the permitted contact window.",
    trainingModule: "Permitted contact windows refresher",
    note: null,
  },
  {
    id: "farid",
    name: "Farid",
    flags: 0,
    pattern: null,
    trainingModule: null,
    note: "No issues this month — conduct patterns consistent with best practice.",
  },
];
