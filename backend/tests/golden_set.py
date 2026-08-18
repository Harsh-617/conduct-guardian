"""Golden set — human-labelled prompt evaluation cases for /screen judgment.

Twenty hand-labelled cases for scoring the LLM's screening judgment against a
human baseline: 7 unambiguous clean messages, 10 clear violations spread
across every LLM-judged rule ID (R5_CONTACT_FREQUENCY is computed from
message timing, not judged from text — see docs/CONDUCT-RULES.md — so it has
no case here), and 3 genuinely borderline calls with a `note` explaining the
judgment call.

Data only. A separate test runner (not this file) is responsible for actually
calling /screen and scoring its verdicts against `GOLDEN_CASES`.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class GoldenCase(TypedDict):
    id: str
    text: str
    expect_violation: bool
    expect_rule: str | None
    # Present only on the 3 borderline cases — explains the judgment call.
    note: NotRequired[str]


GOLDEN_CASES: list[GoldenCase] = [
    # --- Clean (7) ------------------------------------------------------------
    {
        "id": "GS-01",
        "text": (
            "Hi, this is a reminder that your payment of RM450.00 is now 5 "
            "days overdue. Let us know if you'd like to set up a payment plan."
        ),
        "expect_violation": False,
        "expect_rule": None,
    },
    {
        "id": "GS-02",
        "text": (
            "Thank you for your partial payment yesterday. Your remaining "
            "balance is RM620.00. Would a smaller weekly instalment help?"
        ),
        "expect_violation": False,
        "expect_rule": None,
    },
    {
        "id": "GS-03",
        "text": "Good morning, just confirming the best number to reach you on going forward.",
        "expect_violation": False,
        "expect_rule": None,
    },
    {
        "id": "GS-04",
        "text": "We can offer a 60-day deferment given what you've shared with us. I'll send the paperwork today.",
        "expect_violation": False,
        "expect_rule": None,
    },
    {
        "id": "GS-05",
        "text": "Is there a time this week that works better for a short call about your account?",
        "expect_violation": False,
        "expect_rule": None,
    },
    {
        "id": "GS-06",
        "text": "Your account balance is RM1,180.00 as of today. Happy to walk through the full statement if useful.",
        "expect_violation": False,
        "expect_rule": None,
    },
    {
        "id": "GS-07",
        "text": "We noticed your payment didn't go through — no rush, just let us know when you'd like to retry.",
        "expect_violation": False,
        "expect_rule": None,
    },
    # --- Clear violations (10), spread across all 7 LLM-judged rules ---------
    {
        "id": "GS-08",
        "text": "Only a deadbeat like you would keep dodging a debt this small.",
        "expect_violation": True,
        "expect_rule": "R1_ABUSIVE_LANGUAGE",
    },
    {
        "id": "GS-09",
        "text": "You're pathetic — always crying poor instead of just paying what you owe.",
        "expect_violation": True,
        "expect_rule": "R1_ABUSIVE_LANGUAGE",
    },
    {
        "id": "GS-10",
        "text": "Pay by tonight or someone will be knocking on your door.",
        "expect_violation": True,
        "expect_rule": "R2_THREATS",
    },
    {
        "id": "GS-11",
        "text": "Keep ignoring us and see what happens to you.",
        "expect_violation": True,
        "expect_rule": "R2_THREATS",
    },
    {
        "id": "GS-12",
        "text": "You'll be arrested within 48 hours if this isn't paid — the police have already been notified.",
        "expect_violation": True,
        "expect_rule": "R3_FALSE_LEGAL_CLAIM",
    },
    {
        "id": "GS-13",
        "text": "If you don't respond, I'll be calling your workplace to explain why you haven't paid.",
        "expect_violation": True,
        "expect_rule": "R4_THIRD_PARTY_DISCLOSURE",
    },
    {
        "id": "GS-14",
        "text": "This is Inspector Rahman from the Consumer Credit Commission — you need to settle this immediately.",
        "expect_violation": True,
        "expect_rule": "R6_IMPERSONATION",
    },
    {
        "id": "GS-15",
        "text": "I'm calling on behalf of the magistrate's office regarding your case file.",
        "expect_violation": True,
        "expect_rule": "R6_IMPERSONATION",
    },
    {
        "id": "GS-16",
        "text": "We're posting your name and debt amount on our agency's public Instagram tomorrow.",
        "expect_violation": True,
        "expect_rule": "R7_PRIVACY",
    },
    {
        "id": "GS-17",
        "text": "I hear that you're between jobs, but that's not my concern — pay the full amount by Friday or we escalate.",
        "expect_violation": True,
        "expect_rule": "R8_HARDSHIP_IGNORED",
    },
    # --- Borderline (3) — judgment calls, each explained ----------------------
    {
        "id": "GS-18",
        "text": (
            "If this isn't settled by Friday, I'll need to note the account "
            "for our internal recovery review — that's the next step on our "
            "side."
        ),
        "expect_violation": False,
        "expect_rule": None,
        "note": (
            "Reads like an escalation warning, but it describes a real "
            "internal process rather than an illegal threat or false legal "
            "claim — judged clean."
        ),
    },
    {
        "id": "GS-19",
        "text": (
            "I need to be very direct — if we don't resolve this today, "
            "you'll leave me no choice but to take this all the way to make "
            "sure it's settled."
        ),
        "expect_violation": True,
        "expect_rule": "R2_THREATS",
        "note": (
            "Deliberately vague ('take this all the way') rather than "
            "specific — exactly the kind of unspecified scare tactic the "
            "threats rule is meant to catch. Judged as a borderline "
            "violation because it implies escalation without naming "
            "anything legitimate."
        ),
    },
    {
        "id": "GS-20",
        "text": (
            "Since your brother co-signed this loan as guarantor, I'll need "
            "to loop him in on the outstanding balance if we can't resolve "
            "this with you directly."
        ),
        "expect_violation": False,
        "expect_rule": None,
        "note": (
            "Looks like R4 third-party disclosure at a glance, but a "
            "co-signing guarantor is a legitimate party to the debt, not an "
            "unrelated third party — judged clean. R4's rule text now "
            "explicitly carves out co-signers and guarantors, so this "
            "should no longer be a close call for the model."
        ),
    },
]
