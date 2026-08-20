"""Pydantic request/response schemas — the contract the Next.js frontend codes against."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.models import Channel, HardshipType

ORM = ConfigDict(from_attributes=True)


# --- /screen ---------------------------------------------------------------


class ScreenRequest(BaseModel):
    text: str = Field(min_length=1)
    channel: Channel = Channel.whatsapp
    account_id: str = Field(default="4471", description="Account external_id")
    collector_id: int | None = None
    agency_id: int | None = None
    is_customer: bool = False
    occurred_at: dt.datetime | None = None
    # Lets the seeder request the cheaper bulk model. Validated server-side
    # against an allowlist of exactly two configured models — a public endpoint
    # must not let a caller name an arbitrary model and spend the token budget
    # on it.
    use_bulk_model: bool = Field(
        default=False,
        description="Screen with GROQ_MODEL_BULK instead of GROQ_MODEL. For bulk seeding.",
    )


class Verdict(BaseModel):
    """What the LLM returns, after validation. Mirrors the json_schema we send."""

    violation: bool
    rule: str | None = None
    quoted_phrase: str | None = None
    explanation: str
    suggested_rewrite: str | None = None


class ScreenResponse(BaseModel):
    message_id: int
    screening_result_id: int
    verdict: Verdict
    model: str
    latency_ms: int
    ledger_entry_hash: str


# --- /dashboard/stats ------------------------------------------------------


class DashboardPoint(BaseModel):
    date: dt.date
    screened: int
    violations: int


class DashboardStats(BaseModel):
    total_screened: int
    total_violations: int
    violation_rate: float
    active_accounts: int
    open_hardship_cases: int
    chart: list[DashboardPoint]


# --- /timeline/{account_id} ------------------------------------------------


class TimelineMessage(BaseModel):
    model_config = ORM

    id: int
    channel: Channel
    raw_text: str
    is_customer: bool
    occurred_at: dt.datetime
    collector_name: str
    violation: bool | None = None
    rule: str | None = None
    quoted_phrase: str | None = None


class PatternFlag(BaseModel):
    triggered: bool
    rule: str
    label: str
    detail: str
    # False for the burst heuristic, which is not a published limit.
    is_published_limit: bool


class TimelineResponse(BaseModel):
    account_external_id: str
    message_count: int
    messages: list[TimelineMessage]
    patterns: list[PatternFlag]


# --- /accounts ---------------------------------------------------------------


class AccountSummary(BaseModel):
    model_config = ORM

    id: int
    external_id: str


class AccountsResponse(BaseModel):
    accounts: list[AccountSummary]


# --- /ledger ---------------------------------------------------------------


class LedgerEntryOut(BaseModel):
    model_config = ORM

    id: int
    screening_result_id: int
    entry_hash: str
    prev_hash: str | None
    created_at: dt.datetime
    rule: str | None = None
    violation: bool | None = None
    # Joined from the attested message. Without these the Evidence Ledger table
    # and the dashboard's Recent Flags can only render a timestamp and a rule
    # pill — an audit log that doesn't show WHAT was said is not much of an
    # audit log. The hash still attests the screening result, not these fields.
    account_external_id: str | None = None
    channel: Channel | None = None
    snippet: str | None = None
    occurred_at: dt.datetime | None = None


class LedgerPage(BaseModel):
    total: int
    page: int
    page_size: int
    entries: list[LedgerEntryOut]


class VerifyRow(BaseModel):
    id: int
    screening_result_id: int
    stored_hash: str
    computed_hash: str
    ok: bool
    reason: str | None


class VerifyResponse(BaseModel):
    valid: bool
    total: int
    failed: int
    first_broken_id: int | None
    verified_at: dt.datetime
    rows: list[VerifyRow]


# --- /coaching -------------------------------------------------------------


class CoachingRow(BaseModel):
    collector_id: int
    collector_name: str
    total_messages: int
    flagged: int
    flag_rate: float
    top_rule: str | None
    pattern_summary: str | None


class CoachingResponse(BaseModel):
    generated_at: dt.datetime
    cached: bool
    rows: list[CoachingRow]


# --- /hardship -------------------------------------------------------------


class HardshipRow(BaseModel):
    id: int
    message_id: int
    account_external_id: str
    signal_type: HardshipType
    quoted_text: str
    raw_text: str
    occurred_at: dt.datetime
    detected_at: dt.datetime


class HardshipResponse(BaseModel):
    total: int
    rows: list[HardshipRow]


# --- /agencies -------------------------------------------------------------


class AgencyRow(BaseModel):
    agency_id: int
    name: str
    total_messages: int
    violations: int
    compliance_score: float
    grade: str


class AgencyResponse(BaseModel):
    rows: list[AgencyRow]


# --- errors ----------------------------------------------------------------


class ErrorBody(BaseModel):
    """Uniform error shape so the UI can render a retry state instead of crashing."""

    code: str
    message: str
    retryable: bool = False
