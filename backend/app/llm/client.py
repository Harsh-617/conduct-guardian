"""Async Groq client wrapper — the only module that imports the `groq` SDK.

There is deliberately no fake/stub/offline runtime mode here: a missing or
invalid API key must fail loudly (`LLMUnavailable`, code
`llm_not_configured`), never silently degrade into a fabricated verdict.
Tests get an `LLMClient`-conforming fake by constructing their own plain
object — nothing in this module needs to change to support that.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

import groq
from groq import AsyncGroq

from app.config import get_settings


class LLMUnavailable(Exception):
    """Raised whenever the LLM layer cannot produce a usable result.

    `code` is one of the machine-readable codes routers put straight into
    `schemas.ErrorBody`; `retryable` tells the caller (and, via the API
    response, the frontend) whether retrying the same request could
    plausibly succeed.
    """

    def __init__(self, message: str, *, code: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class LLMClient(Protocol):
    """What `screening.py`, `hardship.py`, and `coaching.py` depend on.

    Keeping this a Protocol (not an ABC on `GroqLLMClient`) means tests can
    satisfy it with a bare object that has a matching `complete_json` — no
    `groq` import, no network, no inheritance required.
    """

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int = 800,
    ) -> dict[str, Any]:
        """Run one structured-output completion and return the parsed JSON."""
        ...


#: Models proven at runtime not to accept `response_format: json_schema`.
#: Populated on the first 400 for a given model, so the fallback costs one
#: wasted call per model per process and nothing after that. Not hardcoded:
#: Groq is adding structured-output support model by model, so a static list
#: would silently keep us on the weaker path once support lands.
_NO_JSON_SCHEMA: set[str] = set()

# Compact, not pretty-printed. This string is prepended to every single
# screening call, and Groq's free tier caps both current models at 8,000
# tokens PER MINUTE — indenting the schema for human readability costs real
# demo capacity.
_SCHEMA_INSTRUCTION = (
    "\n\nReturn ONLY a single JSON object matching this schema. "
    "No markdown fences, no commentary:\n{schema}"
)


class GroqLLMClient:
    """Production `LLMClient`, backed by the real Groq API.

    Prefers strict structured output (`response_format: json_schema`) and falls
    back to JSON Object Mode when the model rejects it outright (the old
    llama-3.3-70b and llama-3.1-8b both did). Whether the current models
    (openai/gpt-oss-120b / -20b) need the fallback is discovered at runtime via
    `_NO_JSON_SCHEMA` rather than assumed here — Groq's structured-output
    support varies by model and changes over time.

    The schema is ALSO rendered into the system prompt on every request, not
    just on the fallback path. Under JSON Object Mode the API guarantees valid
    JSON but nothing about its shape, so the prompt is the only thing carrying
    the contract — and `screening._post_validate` is the real enforcement.
    """

    def __init__(self, api_key: str) -> None:
        self._client = AsyncGroq(api_key=api_key, timeout=20.0, max_retries=2)

    async def _create(
        self, *, model: str, system: str, user: str, max_tokens: int, response_format: dict[str, Any]
    ):
        return await self._client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            response_format=response_format,
        )

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int = 800,
    ) -> dict[str, Any]:
        system_with_schema = system + _SCHEMA_INSTRUCTION.format(
            schema=json.dumps(schema, separators=(",", ":"))
        )
        strict_format = {
            "type": "json_schema",
            "json_schema": {"name": "response", "schema": schema, "strict": True},
        }

        try:
            if model in _NO_JSON_SCHEMA:
                response = await self._create(
                    model=model,
                    system=system_with_schema,
                    user=user,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
            else:
                try:
                    response = await self._create(
                        model=model,
                        system=system_with_schema,
                        user=user,
                        max_tokens=max_tokens,
                        response_format=strict_format,
                    )
                except groq.BadRequestError as exc:
                    if "does not support response format" not in str(exc):
                        raise
                    _NO_JSON_SCHEMA.add(model)
                    response = await self._create(
                        model=model,
                        system=system_with_schema,
                        user=user,
                        max_tokens=max_tokens,
                        response_format={"type": "json_object"},
                    )
        # Order matters: RateLimitError and AuthenticationError are both
        # subclasses of APIStatusError, so they must be caught before the
        # generic APIStatusError fallback. APITimeoutError is a subclass of
        # APIConnectionError, not APIStatusError, so it needs its own clause.
        except groq.RateLimitError as exc:
            raise LLMUnavailable(
                str(exc), code="llm_rate_limited", retryable=True
            ) from exc
        except groq.APITimeoutError as exc:
            raise LLMUnavailable(str(exc), code="llm_timeout", retryable=True) from exc
        except groq.AuthenticationError as exc:
            raise LLMUnavailable(str(exc), code="llm_auth", retryable=False) from exc
        except groq.APIStatusError as exc:
            raise LLMUnavailable(
                str(exc), code="llm_error", retryable=exc.status_code >= 500
            ) from exc

        content = response.choices[0].message.content
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            raise LLMUnavailable(
                "model returned non-JSON content",
                code="llm_malformed",
                retryable=True,
            ) from exc

        if not isinstance(parsed, dict):
            raise LLMUnavailable(
                "model returned a JSON value that is not an object",
                code="llm_malformed",
                retryable=True,
            )
        return parsed


def get_llm_client() -> GroqLLMClient:
    """Build the production client from settings.

    Raises `LLMUnavailable(code="llm_not_configured")` instead of returning
    a degraded/fake client — see the module docstring for why.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        raise LLMUnavailable(
            "GROQ_API_KEY is not set", code="llm_not_configured", retryable=False
        )
    return GroqLLMClient(settings.groq_api_key)
