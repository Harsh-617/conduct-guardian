"""Summarise a collector's recurring conduct problem for their manager.

Unlike screening and hardship detection, the caller-facing return here is
plain text (`str`), not a structured record — `CoachingRow.pattern_summary`
in the dashboard renders it directly. Internally it still goes through
`LLMClient.complete_json` with a one-field schema, keeping this module on
the same structured-output path (and the same JSON-decode failure modes) as
the rest of the LLM layer instead of adding a second client method for a
single caller.
"""

from __future__ import annotations

from typing import Any

from .client import LLMClient, LLMUnavailable
from .prompting import LEADING_GUARD, wrap_untrusted

#: Bounds prompt size and cost regardless of how many violations a collector
#: has accumulated.
_MAX_MESSAGES = 15
_MAX_CHARS_PER_MESSAGE = 300

_SUMMARY_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
    "additionalProperties": False,
}


def _build_system_prompt() -> str:
    return (
        "You write short, actionable coaching feedback for a debt "
        "collection team lead. You are given a set of real messages from "
        "one collector that were already flagged as conduct violations. "
        "Summarise the recurring problem across them in 1-2 sentences, "
        "addressed to the collector's manager and framed as actionable "
        "coaching — name the pattern to correct, not just what happened. "
        f"Plain prose in the `summary` field, no markdown, no preamble. "
        f"{LEADING_GUARD}"
    )


def _wrap_messages(flagged_texts: list[str]) -> str:
    """Delimit the collector's flagged messages as data.

    These are the most adversarial input in the whole system: messages already
    judged to be misconduct, written by someone with a motive to influence how
    their own conduct gets summarised to their manager. Same hardening as
    every other untrusted span — see `prompting.wrap_untrusted`.
    """
    sample = flagged_texts[:_MAX_MESSAGES]
    truncated = [t[:_MAX_CHARS_PER_MESSAGE] for t in sample]
    numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(truncated, start=1))
    return wrap_untrusted(
        numbered,
        task_reminder=(
            "Now summarise the recurring conduct problem across those messages "
            "and return the JSON object with the `summary` field."
        ),
    )


async def summarise_collector_pattern(
    client: LLMClient,
    collector_name: str,
    flagged_texts: list[str],
    *,
    model: str,
) -> str:
    """Summarise one collector's recurring conduct problem in 1-2 sentences.

    Caps input at the first 15 messages, each truncated to 300 characters.
    Returns plain text — see the module docstring for why this still goes
    through `complete_json` under the hood.
    """
    system = _build_system_prompt()
    user = f"Collector: {collector_name}\n\n{_wrap_messages(flagged_texts)}"

    raw = await client.complete_json(
        system=system,
        user=user,
        schema=_SUMMARY_JSON_SCHEMA,
        model=model,
    )
    summary = raw.get("summary")
    if not isinstance(summary, str):
        # `complete_json` already raises LLMUnavailable for unparsable JSON;
        # this covers the narrower case of parsable-but-wrong-shaped JSON
        # (missing/mistyped `summary`). Raising the same error here, rather
        # than a bare KeyError, matters because the /coaching router only
        # catches LLMUnavailable — an uncaught KeyError would 500 the whole
        # leaderboard instead of just leaving one collector's summary blank.
        raise LLMUnavailable(
            "model returned a malformed coaching summary",
            code="llm_malformed",
            retryable=True,
        )
    return summary
