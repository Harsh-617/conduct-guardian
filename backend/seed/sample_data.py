"""Synthetic seed data for Conduct Guardian.

Pure data — no DB or network imports, so this module can be inspected, unit
tested, or reused by `tests/golden_set.py`-style consumers without touching a
database. Everything here is fictional: no real person, company, or phone
number. Malaysian-flavoured names and RM currency for continuity with the UI
mockup, which already uses account "4471" and collector "Ravi".

`docs/CONDUCT-RULES.md` is the source of truth for the 8 rule IDs. R5 is
deliberately absent from `MESSAGE_TEMPLATES` below — it's computed from
message timing in SQL, never judged from text (see `app/rules.py`).
"""

from __future__ import annotations

import datetime as dt
import random
from typing import TypedDict


class AgencySeed(TypedDict):
    name: str


class CollectorSeed(TypedDict):
    name: str
    role: str


class AccountSeed(TypedDict):
    external_id: str


class MessageTemplate(TypedDict):
    text: str
    # Human label for what SHOULD be flagged. None = clean/acceptable.
    expected_rule: str | None
    # True when this is the borrower speaking, not the collector.
    is_customer: bool


class PlannedMessage(TypedDict):
    account_external_id: str
    collector_name: str
    agency_name: str
    channel: str
    text: str
    is_customer: bool
    occurred_at: dt.datetime
    #: The human label for what SHOULD be flagged. Never sent to the API — it
    #: exists so the seeder can score the model's real verdicts against it.
    expected_rule: str | None


# --- Agencies, collectors, accounts -----------------------------------------

AGENCIES: list[AgencySeed] = [
    {"name": "Kredit Selesai Sdn Bhd"},
    {"name": "Prima Recovery Solutions"},
    {"name": "Amanah Debt Services"},
    {"name": "Sinar Kredit Management"},
]

# Six collectors, including "Ravi" — the name already used in the UI mockup.
COLLECTORS: list[CollectorSeed] = [
    {"name": "Ravi Krishnan", "role": "Senior Collector"},
    {"name": "Farah Aziz", "role": "Collector"},
    {"name": "Wei Ming Tan", "role": "Collector"},
    {"name": "Nurul Huda", "role": "Collector"},
    {"name": "Suresh Pillai", "role": "Team Lead"},
    {"name": "Aisyah Rahman", "role": "Collector"},
]

# Eight accounts, including "4471" — the reference already used in the UI mockup.
ACCOUNTS: list[AccountSeed] = [
    {"external_id": "4471"},
    {"external_id": "5820"},
    {"external_id": "3392"},
    {"external_id": "6104"},
    {"external_id": "2277"},
    {"external_id": "8865"},
    {"external_id": "1543"},
    {"external_id": "7710"},
]


# --- Message templates -------------------------------------------------------
#
# Coverage: ~15 clean, 4 per LLM-judged rule (R1/R2/R3/R4/R6/R7/R8 — R5 is
# computed, never text-judged), ~8 borderline, 6 customer-side hardship
# disclosures. 57 templates total, well over the 45 minimum.

MESSAGE_TEMPLATES: list[MessageTemplate] = [
    # --- Clean, professional (15) -------------------------------------------
    {
        "text": (
            "Good afternoon, this is a reminder that your payment of RM1,250.00 "
            "for account ending 4471 is now 15 days overdue. Please let us know "
            "if you'd like to arrange a payment plan."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "Hi, just following up on the outstanding balance of RM860.50. You "
            "can make a payment via our online portal or call us back at your "
            "convenience."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "Thank you for your payment of RM300 received yesterday. Your "
            "remaining balance is RM540.00. Let us know if you have any "
            "questions."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "We noticed your last payment did not go through. Would you like "
            "to reschedule for a different date this week?"
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "This is a courtesy call regarding your account. There is no need "
            "to worry — we just want to confirm a convenient time to discuss "
            "your repayment options."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "Good morning, may I confirm your mailing address so we can send "
            "you the updated statement of account?"
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "We understand things can be tight. Would a smaller weekly "
            "instalment work better for you than the current monthly amount?"
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": "Your account is eligible for a restructuring plan. Would you like me to email you the details?",
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "Just a gentle reminder that your payment date is coming up on "
            "the 28th. Let us know if you need any assistance."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "We've received your query about the interest calculation. I'll "
            "have our finance team send a full breakdown by email today."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": "Thank you for calling in to update your contact number. I've updated it in our system.",
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "Is there a better time for us to call you regarding your "
            "account? We want to make sure we're not disturbing you at work."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "Your outstanding balance as of today is RM2,140.00. Would you "
            "like to review the full statement together?"
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": "We can offer a 3-month deferment if you're able to share more about your current situation.",
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "Hi, this is Farah from Prima Recovery Solutions. I'm calling to "
            "check in on your account, nothing urgent — just want to see how "
            "we can help."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    # --- R1_ABUSIVE_LANGUAGE (4) --------------------------------------------
    {
        "text": "You people are useless, always making excuses instead of paying what you owe.",
        "expected_rule": "R1_ABUSIVE_LANGUAGE",
        "is_customer": False,
    },
    {
        "text": "Stop being so lazy and pay your debt, everyone else manages to pay on time.",
        "expected_rule": "R1_ABUSIVE_LANGUAGE",
        "is_customer": False,
    },
    {
        "text": "Only an irresponsible person would ignore their debt like this.",
        "expected_rule": "R1_ABUSIVE_LANGUAGE",
        "is_customer": False,
    },
    {
        "text": "You're a disgrace to your family, always dodging your responsibilities.",
        "expected_rule": "R1_ABUSIVE_LANGUAGE",
        "is_customer": False,
    },
    # --- R2_THREATS (4) ------------------------------------------------------
    {
        "text": "If you don't pay by tomorrow, we will send people to your house.",
        "expected_rule": "R2_THREATS",
        "is_customer": False,
    },
    {
        "text": "Pay now or we will make sure you regret it.",
        "expected_rule": "R2_THREATS",
        "is_customer": False,
    },
    {
        "text": "We know where you work and where you live — don't test us.",
        "expected_rule": "R2_THREATS",
        "is_customer": False,
    },
    {
        "text": "If this isn't settled today, things will get very ugly for you.",
        "expected_rule": "R2_THREATS",
        "is_customer": False,
    },
    # --- R3_FALSE_LEGAL_CLAIM (4) --------------------------------------------
    {
        "text": "If you don't pay within 24 hours, the police will come and arrest you.",
        "expected_rule": "R3_FALSE_LEGAL_CLAIM",
        "is_customer": False,
    },
    {
        "text": "You will be blacklisted and jailed if this isn't settled by Friday.",
        "expected_rule": "R3_FALSE_LEGAL_CLAIM",
        "is_customer": False,
    },
    {
        "text": "Our lawyer has already filed a case against you in court this morning.",
        "expected_rule": "R3_FALSE_LEGAL_CLAIM",
        "is_customer": False,
    },
    {
        "text": "Failure to pay today means a warrant will be issued for your arrest.",
        "expected_rule": "R3_FALSE_LEGAL_CLAIM",
        "is_customer": False,
    },
    # --- R4_THIRD_PARTY_DISCLOSURE (4) ---------------------------------------
    {
        "text": "If you don't pay, we will call your office manager and explain why you're avoiding us.",
        "expected_rule": "R4_THIRD_PARTY_DISCLOSURE",
        "is_customer": False,
    },
    {
        "text": "We're going to tell your neighbours about your unpaid debt if this continues.",
        "expected_rule": "R4_THIRD_PARTY_DISCLOSURE",
        "is_customer": False,
    },
    {
        "text": "I'll contact your sister since you're not responding — she can help settle this for you.",
        "expected_rule": "R4_THIRD_PARTY_DISCLOSURE",
        "is_customer": False,
    },
    {
        "text": "We'll post about your debt in your residents' WhatsApp group if you keep ignoring us.",
        "expected_rule": "R4_THIRD_PARTY_DISCLOSURE",
        "is_customer": False,
    },
    # --- R6_IMPERSONATION (4) -------------------------------------------------
    {
        "text": "This is Officer Zulkifli from the Consumer Credit Commission calling about your case.",
        "expected_rule": "R6_IMPERSONATION",
        "is_customer": False,
    },
    {
        "text": "I'm calling from the court registry to inform you of your hearing date.",
        "expected_rule": "R6_IMPERSONATION",
        "is_customer": False,
    },
    {
        "text": "This is your lawyer's office — we need to discuss the charges against you.",
        "expected_rule": "R6_IMPERSONATION",
        "is_customer": False,
    },
    {
        "text": "I'm a police liaison officer assigned to debt recovery cases in your area.",
        "expected_rule": "R6_IMPERSONATION",
        "is_customer": False,
    },
    # --- R7_PRIVACY (4) --------------------------------------------------------
    {
        "text": "We're going to post your name and photo on our recovery agency's Facebook page.",
        "expected_rule": "R7_PRIVACY",
        "is_customer": False,
    },
    {
        "text": "Everyone in the office already knows about your unpaid loan, by the way.",
        "expected_rule": "R7_PRIVACY",
        "is_customer": False,
    },
    {
        "text": "We've shared your debt details with our partner agencies so they can pressure you too.",
        "expected_rule": "R7_PRIVACY",
        "is_customer": False,
    },
    {
        "text": "I'll make sure your community WhatsApp group hears about this if you don't respond.",
        "expected_rule": "R7_PRIVACY",
        "is_customer": False,
    },
    # --- R8_HARDSHIP_IGNORED (4) -------------------------------------------------
    {
        "text": "I understand you lost your job, but that's not our problem — you still need to pay by Friday.",
        "expected_rule": "R8_HARDSHIP_IGNORED",
        "is_customer": False,
    },
    {
        "text": "Hospital bills or not, the payment is due today. We can't keep waiting.",
        "expected_rule": "R8_HARDSHIP_IGNORED",
        "is_customer": False,
    },
    {
        "text": "I know your father passed away, but the debt doesn't go away with him — please settle this week.",
        "expected_rule": "R8_HARDSHIP_IGNORED",
        "is_customer": False,
    },
    {
        "text": "You said you have no income, but we still need at least a partial payment by tomorrow or we'll escalate.",
        "expected_rule": "R8_HARDSHIP_IGNORED",
        "is_customer": False,
    },
    # --- Borderline (8) — firm but arguably acceptable ------------------------
    {
        "text": (
            "This is now our fourth attempt to reach you this month. Please "
            "respond so we can avoid further action."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "If we don't hear from you by Friday, this account will be "
            "forwarded to our recovery unit for review."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": "Your account will be flagged as delinquent in our system if payment isn't received by the 30th.",
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "I have to be upfront — if this goes unpaid another 30 days, it "
            "will start affecting your credit score with other lenders."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "We've called three times already this week. I really need you "
            "to commit to a date today, otherwise I'll have to note this "
            "account for supervisor review."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": "You've missed the deadline again. I'm not going to sugarcoat it — this is now a serious situation for your account.",
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": (
            "We've held off reporting this to the credit bureau so far, but "
            "that changes if we don't hear from you by Monday."
        ),
        "expected_rule": None,
        "is_customer": False,
    },
    {
        "text": "If you can't pay in full, I need at least a partial payment today, otherwise I'll have to mark this account as high risk.",
        "expected_rule": None,
        "is_customer": False,
    },
    # --- Customer-side hardship disclosures (6) ------------------------------
    {
        "text": (
            "I lost my job three weeks ago and I've been applying "
            "everywhere, but nothing yet. I honestly don't have the money "
            "right now."
        ),
        "expected_rule": None,
        "is_customer": True,
    },
    {
        "text": (
            "My daughter was hospitalised last week and the medical bills "
            "wiped out our savings. I can't pay the full amount right now."
        ),
        "expected_rule": None,
        "is_customer": True,
    },
    {
        "text": (
            "My father passed away last month and I've been dealing with "
            "funeral costs and my mother's expenses. I need some time."
        ),
        "expected_rule": None,
        "is_customer": True,
    },
    {
        "text": (
            "I haven't had any income since the company shut down in March. "
            "I really don't know how I'm going to manage this payment."
        ),
        "expected_rule": None,
        "is_customer": True,
    },
    {
        "text": (
            "I was retrenched last month along with half my department. I'm "
            "actively job hunting but there's nothing lined up yet."
        ),
        "expected_rule": None,
        "is_customer": True,
    },
    {
        "text": (
            "I've been in and out of the hospital for the past two months "
            "and haven't been able to work. There's simply no income coming "
            "in right now."
        ),
        "expected_rule": None,
        "is_customer": True,
    },
]


CHANNELS: tuple[str, ...] = ("whatsapp", "sms", "call", "email")


def _clean_pool() -> list[MessageTemplate]:
    return [t for t in MESSAGE_TEMPLATES if t["expected_rule"] is None and not t["is_customer"]]


def _violation_pool() -> list[MessageTemplate]:
    return [t for t in MESSAGE_TEMPLATES if t["expected_rule"] is not None]


def _hardship_pool() -> list[MessageTemplate]:
    return [t for t in MESSAGE_TEMPLATES if t["is_customer"]]


def build_message_plan(now: dt.datetime, days: int = 14) -> list[PlannedMessage]:
    """Build ~80 timed, planned messages across all accounts.

    Deterministic: seeded with `random.Random(1337)`, never wall-clock time.
    Callers must pass `now` explicitly so re-running the plan produces
    identical timestamps for the same `now`.

    Account "4471" deliberately gets a dense cluster — 5 messages inside a
    single 60-minute window on one day. That single cluster both breaches
    BNM's 3-contacts-per-week limit (R5_CONTACT_FREQUENCY, computed in SQL —
    see `app/rules.py`) and trips the secondary same-hour burst heuristic
    (BURST_CONTACT_COUNT=5 / BURST_WINDOW_MINUTES=60), giving the timeline
    pattern detection something real to find in the demo.
    """
    rng = random.Random(1337)
    plan: list[PlannedMessage] = []

    clean_pool = _clean_pool()
    violation_pool = _violation_pool()
    hardship_pool = _hardship_pool()

    def rand_time(day_offset_max: float) -> dt.datetime:
        day_offset = rng.uniform(0, day_offset_max)
        ts = now - dt.timedelta(days=day_offset)
        return ts.replace(
            hour=rng.randint(9, 20),
            minute=rng.randint(0, 59),
            second=rng.randint(0, 59),
            microsecond=0,
        )

    def make_message(
        account_external_id: str, template: MessageTemplate, occurred_at: dt.datetime
    ) -> PlannedMessage:
        return {
            "account_external_id": account_external_id,
            "collector_name": rng.choice(COLLECTORS)["name"],
            "agency_name": rng.choice(AGENCIES)["name"],
            "channel": rng.choice(CHANNELS),
            "text": template["text"],
            "is_customer": template["is_customer"],
            "occurred_at": occurred_at,
            # Carried through so the seeder can compare the real model verdict
            # against a human label across the whole corpus. That agreement
            # rate over ~75 messages is a far stronger accuracy claim than the
            # 20-case golden set alone, and it costs nothing to collect since
            # every message is being screened anyway.
            "expected_rule": template["expected_rule"],
        }

    # --- Account 4471: the deliberate breach cluster ------------------------
    ext_4471 = "4471"
    burst_day_offset = rng.randint(3, max(4, min(days - 1, 8)))
    burst_anchor = (now - dt.timedelta(days=burst_day_offset)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    burst_minutes = sorted(rng.sample(range(0, 60), 5))
    burst_texts = rng.sample(violation_pool, k=5)
    for minute, template in zip(burst_minutes, burst_texts):
        plan.append(make_message(ext_4471, template, burst_anchor + dt.timedelta(minutes=minute)))

    # A hardship disclosure a couple of days later, followed by a collector
    # message that ignores it — R8_HARDSHIP_IGNORED, with continuity between
    # the two messages so the hardship queue and the timeline tell one story.
    hardship_entry = hardship_pool[0]
    hardship_time = burst_anchor + dt.timedelta(days=2, hours=3)
    plan.append(make_message(ext_4471, hardship_entry, hardship_time))

    r8_entry = next(t for t in violation_pool if t["expected_rule"] == "R8_HARDSHIP_IGNORED")
    plan.append(make_message(ext_4471, r8_entry, hardship_time + dt.timedelta(days=1, hours=2)))

    for _ in range(4):
        plan.append(make_message(ext_4471, rng.choice(clean_pool), rand_time(days)))

    # --- Remaining accounts: normal spread -----------------------------------
    other_accounts = [a["external_id"] for a in ACCOUNTS if a["external_id"] != ext_4471]
    remaining_hardship = hardship_pool[1:]
    hardship_assignment = dict(
        zip(rng.sample(other_accounts, k=len(remaining_hardship)), remaining_hardship)
    )

    for ext_id in other_accounts:
        for _ in range(rng.randint(8, 10)):
            # Skew toward clean/borderline, like a real book of accounts.
            template = rng.choice(clean_pool) if rng.random() < 0.6 else rng.choice(violation_pool)
            plan.append(make_message(ext_id, template, rand_time(days)))
        if ext_id in hardship_assignment:
            plan.append(make_message(ext_id, hardship_assignment[ext_id], rand_time(days)))

    plan.sort(key=lambda m: m["occurred_at"])
    return plan
