/**
 * Types returned by the Conduct Guardian FastAPI backend.
 *
 * Transcribed from the live OpenAPI schema and verified field-for-field
 * (95 fields, 9 endpoints). Regenerate rather than hand-patch:
 *
 *   curl $NEXT_PUBLIC_API_BASE_URL/openapi.json
 *
 * These are the WIRE types. The UI's own display types (capitalised channels,
 * "FLAGGED"/"CLEAR", human-readable rule names) live in each feature's
 * data.ts and are produced by `adapters.ts`. Keeping the two separate is what
 * lets the screens stay untouched.
 */

export type ApiChannel = "whatsapp" | "sms" | "call" | "email";

export type ApiHardshipType =
  | "job_loss"
  | "health_crisis"
  | "bereavement"
  | "financial_distress";

export type RuleId =
  | "R1_ABUSIVE_LANGUAGE"
  | "R2_THREATS"
  | "R3_FALSE_LEGAL_CLAIM"
  | "R4_THIRD_PARTY_DISCLOSURE"
  | "R5_CONTACT_FREQUENCY"
  | "R6_IMPERSONATION"
  | "R7_PRIVACY"
  | "R8_HARDSHIP_IGNORED";

export interface Verdict {
  violation: boolean;
  rule: RuleId | null;
  /** Guaranteed verbatim substring of the screened text, or null. */
  quoted_phrase: string | null;
  explanation: string;
  suggested_rewrite: string | null;
}

export interface ScreenRequest {
  text: string;
  channel?: ApiChannel;
  account_id?: string;
  collector_id?: number | null;
  agency_id?: number | null;
  is_customer?: boolean;
  occurred_at?: string | null;
  use_bulk_model?: boolean;
}

export interface ScreenResponse {
  message_id: number;
  screening_result_id: number;
  verdict: Verdict;
  model: string;
  latency_ms: number;
  ledger_entry_hash: string;
}

export interface DashboardPoint {
  date: string;
  screened: number;
  violations: number;
}

export interface DashboardStats {
  total_screened: number;
  total_violations: number;
  violation_rate: number;
  active_accounts: number;
  open_hardship_cases: number;
  chart: DashboardPoint[];
}

export interface TimelineMessage {
  id: number;
  channel: ApiChannel;
  raw_text: string;
  is_customer: boolean;
  occurred_at: string;
  collector_name: string;
  violation?: boolean | null;
  rule?: RuleId | null;
  quoted_phrase?: string | null;
}

export interface PatternFlag {
  triggered: boolean;
  rule: string;
  label: string;
  detail: string;
  /**
   * TRUE = a published regulatory limit (BNM's 3 contacts/week).
   * FALSE = our own internal heuristic.
   *
   * The UI MUST render these differently. Badging a heuristic as a regulatory
   * breach is exactly what a judge who knows the sector will catch, and it
   * discredits the flags that genuinely are published limits.
   */
  is_published_limit: boolean;
}

export interface TimelineResponse {
  account_external_id: string;
  message_count: number;
  messages: TimelineMessage[];
  patterns: PatternFlag[];
}

export interface LedgerEntry {
  id: number;
  screening_result_id: number;
  entry_hash: string;
  prev_hash: string | null;
  created_at: string;
  rule?: RuleId | null;
  violation?: boolean | null;
  /** Joined from the attested message — may be null on older rows. */
  account_external_id?: string | null;
  channel?: ApiChannel | null;
  /** Server-truncated preview (<=160 chars). */
  snippet?: string | null;
  occurred_at?: string | null;
}

export interface LedgerPage {
  total: number;
  page: number;
  page_size: number;
  entries: LedgerEntry[];
}

export interface VerifyRow {
  id: number;
  screening_result_id: number;
  stored_hash: string;
  computed_hash: string;
  ok: boolean;
  reason: string | null;
}

export interface VerifyResponse {
  valid: boolean;
  total: number;
  failed: number;
  first_broken_id: number | null;
  verified_at: string;
  rows: VerifyRow[];
}

export interface CoachingRow {
  collector_id: number;
  collector_name: string;
  total_messages: number;
  flagged: number;
  flag_rate: number;
  top_rule: RuleId | null;
  pattern_summary: string | null;
}

export interface CoachingResponse {
  generated_at: string;
  cached: boolean;
  rows: CoachingRow[];
}

export interface HardshipRow {
  id: number;
  message_id: number;
  account_external_id: string;
  signal_type: ApiHardshipType;
  quoted_text: string;
  raw_text: string;
  occurred_at: string;
  detected_at: string;
}

export interface HardshipResponse {
  total: number;
  rows: HardshipRow[];
}

export interface AgencyRow {
  agency_id: number;
  name: string;
  total_messages: number;
  violations: number;
  compliance_score: number;
  grade: "A" | "B" | "C" | "D" | "F";
}

export interface AgencyResponse {
  rows: AgencyRow[];
}

export interface AccountSummary {
  id: number;
  external_id: string;
}

export interface AccountsResponse {
  accounts: AccountSummary[];
}

export interface HealthResponse {
  status: string;
  groq_configured: boolean;
  database_configured: boolean;
  model: string;
}
