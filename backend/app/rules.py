"""The conduct rule pack.

Data, not prose baked into a prompt. `docs/CONDUCT-RULES.md` is the source of
truth for every rule here, and every rule carries a public citation.

Why this file exists as data: the SKP Conduct Standards v1.0 (5 Jun 2026) is a
Restricted document we cannot obtain. The demo story is "swap the pack, keep the
engine" — that claim is only honest if the pack really is swappable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    looks_for: str
    source: str
    # LLM-judged rules go in the prompt. Computed rules are evaluated in SQL and
    # must never be handed to the model — determinism is the whole point.
    llm_judged: bool = True


RULES: tuple[Rule, ...] = (
    Rule(
        id="R1_ABUSIVE_LANGUAGE",
        title="No abusive, humiliating, or intimidating language",
        looks_for=(
            "Insults, slurs, name-calling, or degrading characterisations of "
            "the borrower or their family."
        ),
        source="BNM Fair Debt Collection Practices",
    ),
    Rule(
        id="R2_THREATS",
        title="No threats, scare tactics, or threatened illegal action",
        looks_for=(
            "Threatened violence, arrest, property seizure without legal basis, "
            "trespass, or 'we will come to your house' style intimidation."
        ),
        source="BNM Fair Debt Collection Practices",
    ),
    Rule(
        id="R3_FALSE_LEGAL_CLAIM",
        title="No misrepresenting legal consequences or authority",
        looks_for=(
            "Claiming imminent arrest, jail, blacklisting, or court action that "
            "is not actually in progress; overstating what the creditor can do."
        ),
        source="Consumer Credit Act 2025 (Act 873) s.85(1)(g)",
    ),
    Rule(
        id="R4_THIRD_PARTY_DISCLOSURE",
        title="Debt must not be disclosed to third parties",
        looks_for=(
            "Naming, contacting, or threatening to tell the borrower's employer, "
            "family, neighbours, or friends about the debt."
        ),
        source="BNM: collectors must deal with the borrower directly",
    ),
    Rule(
        id="R5_CONTACT_FREQUENCY",
        title="No more than 3 contacts per week",
        looks_for=(
            "Computed from message history in SQL — never judged by the model."
        ),
        source="BNM: no more than 3 calls per week",
        llm_judged=False,
    ),
    Rule(
        id="R6_IMPERSONATION",
        title="No impersonating officials, lawyers, or law enforcement",
        looks_for=(
            "Presenting as police, a court officer, a government agency, or a "
            "lawyer when the sender is a collection agent."
        ),
        source="Consumer Credit Act 2025 (Act 873) fair-dealing intent",
    ),
    Rule(
        id="R7_PRIVACY",
        title="Borrower privacy and dignity must be protected",
        looks_for=(
            "Publicising the debt, public shaming, or sharing the borrower's "
            "personal data with anyone not party to the debt."
        ),
        source="Act 873; BNM privacy and human-rights framing",
    ),
    Rule(
        id="R8_HARDSHIP_IGNORED",
        title="Genuine hardship must route to review, not escalation",
        looks_for=(
            "Continued pressure, demands, or threats after the borrower has "
            "clearly disclosed job loss, illness, bereavement, or destitution."
        ),
        source="Act 873 fair-treatment intent",
    ),
)

RULES_BY_ID: dict[str, Rule] = {r.id: r for r in RULES}

#: Rules the LLM is asked to judge. R5 is excluded by design.
LLM_RULES: tuple[Rule, ...] = tuple(r for r in RULES if r.llm_judged)

#: BNM's published limit, used by the computed R5 check.
MAX_CONTACTS_PER_WEEK = 3

#: Secondary harassment heuristic. NOT a published limit — label it as such
#: anywhere it surfaces in the UI, or a judge will rightly ask "says who?".
BURST_CONTACT_COUNT = 5
BURST_WINDOW_MINUTES = 60


def rules_for_prompt() -> str:
    """Render the LLM-judged rules as a numbered block for the system prompt."""
    lines = []
    for rule in LLM_RULES:
        lines.append(f"- {rule.id}: {rule.title}. Look for: {rule.looks_for}")
    return "\n".join(lines)


def is_valid_rule_id(rule_id: str | None) -> bool:
    """Guard against the model inventing a rule ID."""
    return rule_id is None or rule_id in RULES_BY_ID
