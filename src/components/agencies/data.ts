export type Trend = "improving" | "declining" | "stable";

export type Agency = {
  id: string;
  name: string;
  score: number;
  flags: number;
  trend: Trend;
};

export const agencies: Agency[] = [
  {
    id: "prestige-recovery-solutions",
    name: "Prestige Recovery Solutions",
    score: 58,
    flags: 14,
    trend: "declining",
  },
  {
    id: "ascend-credit-services",
    name: "Ascend Credit Services",
    score: 71,
    flags: 9,
    trend: "declining",
  },
  {
    id: "meridian-collections-group",
    name: "Meridian Collections Group",
    score: 79,
    flags: 6,
    trend: "stable",
  },
  {
    id: "sentinel-debt-recovery",
    name: "Sentinel Debt Recovery",
    score: 88,
    flags: 3,
    trend: "improving",
  },
  {
    id: "northgate-asset-recovery",
    name: "Northgate Asset Recovery",
    score: 94,
    flags: 1,
    trend: "improving",
  },
].sort((a, b) => a.score - b.score);
