"""Tests for the conduct rule pack (app/rules.py).

docs/CONDUCT-RULES.md is the source of truth this file is checked against —
drift between the two (a renamed id, a rule that silently starts reaching the
model) is exactly what these tests exist to catch.
"""

from __future__ import annotations

from app.rules import (
    LLM_RULES,
    MAX_CONTACTS_PER_WEEK,
    RULES,
    RULES_BY_ID,
    is_valid_rule_id,
    rules_for_prompt,
)

#: The 8 rule IDs in docs/CONDUCT-RULES.md's "Rule pack v1" table.
DOCUMENTED_RULE_IDS = {
    "R1_ABUSIVE_LANGUAGE",
    "R2_THREATS",
    "R3_FALSE_LEGAL_CLAIM",
    "R4_THIRD_PARTY_DISCLOSURE",
    "R5_CONTACT_FREQUENCY",
    "R6_IMPERSONATION",
    "R7_PRIVACY",
    "R8_HARDSHIP_IGNORED",
}


def test_rule_ids_are_unique_and_match_the_documented_pack():
    ids = [rule.id for rule in RULES]

    assert len(ids) == len(set(ids)), "duplicate rule id in RULES"
    assert set(ids) == DOCUMENTED_RULE_IDS


def test_r5_contact_frequency_is_not_llm_judged():
    r5 = RULES_BY_ID["R5_CONTACT_FREQUENCY"]

    assert r5.llm_judged is False
    assert r5 not in LLM_RULES
    assert all(rule.id != "R5_CONTACT_FREQUENCY" for rule in LLM_RULES)


def test_rules_for_prompt_covers_every_llm_rule_and_excludes_r5():
    prompt = rules_for_prompt()

    for rule in LLM_RULES:
        assert rule.id in prompt

    assert "R5_CONTACT_FREQUENCY" not in prompt


def test_is_valid_rule_id_rejects_invented_ids_and_accepts_none():
    assert is_valid_rule_id(None) is True
    assert is_valid_rule_id("R1_ABUSIVE_LANGUAGE") is True
    assert is_valid_rule_id("R99_MADE_UP") is False
    assert is_valid_rule_id("") is False


def test_max_contacts_per_week_matches_bnms_published_limit():
    # BNM's published limit is 3 calls/week. A regression here would silently
    # weaken the product's central compliance claim.
    assert MAX_CONTACTS_PER_WEEK == 3
