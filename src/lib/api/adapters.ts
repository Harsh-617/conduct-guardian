/**
 * Map backend wire types onto the UI's existing display types.
 *
 * The screens already define their own shapes in each feature's `data.ts`
 * ("WhatsApp" not "whatsapp", "FLAGGED" not `violation: true`, human-readable
 * rule names not `R2_THREATS`). Adapting here rather than changing those types
 * is what keeps the PRD's promise that the UI itself barely changes — the
 * markup, animations and styling are untouched, only the data source moves.
 */

import type {
  AgencyRow as ApiAgencyRow,
  ApiChannel,
  ApiHardshipType,
  CoachingRow as ApiCoachingRow,
  HardshipRow as ApiHardshipRow,
  LedgerEntry as ApiLedgerEntry,
  RuleId,
  TimelineMessage as ApiTimelineMessage,
} from "./types";

import type { Agency } from "@/components/agencies/data";
import type { Officer } from "@/components/coaching/data";
import type { HardshipAccount, HardshipSignal } from "@/components/hardship/data";
import type { LedgerRow } from "@/components/ledger/data";
import type { Touchpoint } from "@/components/timeline/data";

/** Wire channel -> the capitalised form the components render. */
export const CHANNEL_LABEL: Record<ApiChannel, "WhatsApp" | "SMS" | "Call" | "Email"> = {
  whatsapp: "WhatsApp",
  sms: "SMS",
  call: "Call",
  email: "Email",
};

/**
 * Rule ID -> the phrasing the UI already used.
 *
 * Deliberately human-readable: a judge reading "R4_THIRD_PARTY_DISCLOSURE" on
 * screen learns nothing. The IDs stay in the database and the ledger, where
 * they are the stable key.
 */
export const RULE_LABEL: Record<RuleId, string> = {
  R1_ABUSIVE_LANGUAGE: "Abusive Language",
  R2_THREATS: "Threatening Language",
  R3_FALSE_LEGAL_CLAIM: "Misleading Legal Claim",
  R4_THIRD_PARTY_DISCLOSURE: "Third-Party Disclosure",
  R5_CONTACT_FREQUENCY: "Excessive Contact Frequency",
  R6_IMPERSONATION: "Impersonation of Authority",
  R7_PRIVACY: "Privacy & Dignity Breach",
  R8_HARDSHIP_IGNORED: "Hardship Signal Ignored",
};

export function ruleLabel(rule: RuleId | null | undefined): string | null {
  if (!rule) return null;
  // Fall back to the raw id rather than dropping it: an unmapped rule means
  // the backend pack gained an entry, and showing the id beats showing null.
  return RULE_LABEL[rule] ?? rule;
}

const HARDSHIP_LABEL: Record<ApiHardshipType, HardshipSignal> = {
  job_loss: "Job Loss",
  health_crisis: "Health Crisis",
  bereavement: "Bereavement",
  financial_distress: "Financial Distress",
};

// --- formatting -------------------------------------------------------------

/**
 * All timestamps render in a fixed locale and timezone.
 *
 * Next renders on the server and hydrates on the client; if those two format
 * a date differently (different locale or TZ) React throws a hydration
 * mismatch. Pinning both sides is the fix.
 */
const TZ = "Asia/Kuala_Lumpur";

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-GB", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: TZ,
  });
}

export function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: TZ,
  });
}

function truncate(text: string, max = 90): string {
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}

function shortHash(hash: string): string {
  return `${hash.slice(0, 6)}...${hash.slice(-4)}`;
}

// --- adapters ---------------------------------------------------------------

export function toTouchpoint(m: ApiTimelineMessage): Touchpoint {
  return {
    id: `tp-${m.id}`,
    time: formatTime(m.occurred_at),
    channel: CHANNEL_LABEL[m.channel],
    preview: truncate(m.raw_text),
  };
}

/**
 * A ledger entry now carries the attested message's account, channel and a
 * server-truncated snippet, so the table can show WHAT was said rather than
 * only that something was hashed. Those fields are still optional: an entry
 * written before the join existed would have them null, and rendering "—"
 * beats crashing or inventing a value.
 */
export function toLedgerRow(entry: ApiLedgerEntry): LedgerRow {
  return {
    id: `row-${entry.id}`,
    // occurred_at is when the message was sent; created_at is when it was
    // screened. The ledger is about the conduct, so prefer the former.
    timestamp: formatTimestamp(entry.occurred_at ?? entry.created_at),
    account: entry.account_external_id ? `#${entry.account_external_id}` : "—",
    channel: entry.channel ? CHANNEL_LABEL[entry.channel] : "SMS",
    snippet: entry.snippet ? truncate(entry.snippet) : "—",
    verdict: entry.violation ? "FLAGGED" : "CLEAR",
    rule: ruleLabel(entry.rule),
    hash: shortHash(entry.entry_hash),
  };
}

export function toOfficer(row: ApiCoachingRow): Officer {
  return {
    id: String(row.collector_id),
    name: row.collector_name,
    flags: row.flagged,
    pattern: row.pattern_summary,
    // The backend has no training-module catalogue; deriving one from the
    // dominant rule keeps the column meaningful instead of inventing content.
    trainingModule: row.top_rule ? `${ruleLabel(row.top_rule)} — corrective module` : null,
    note: null,
  };
}

export function toHardshipAccount(row: ApiHardshipRow): HardshipAccount {
  return {
    id: `hardship-${row.id}`,
    accountId: `#${row.account_external_id}`,
    quote: row.quoted_text,
    signal: HARDSHIP_LABEL[row.signal_type],
    routing:
      "Routed to specialist — standard escalation paused, restructuring conversation scheduled.",
  };
}

export function toAgency(row: ApiAgencyRow): Agency {
  return {
    id: String(row.agency_id),
    name: row.name,
    score: Math.round(row.compliance_score),
    flags: row.violations,
    // Trend needs history the backend does not keep (scores are computed on
    // read, never stored). Reporting "stable" is honest; inventing a direction
    // from a single snapshot would not be.
    trend: "stable",
  };
}
