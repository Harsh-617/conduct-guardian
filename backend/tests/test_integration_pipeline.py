"""End-to-end integration test over the real HTTP app.

This drives the actual FastAPI application through `httpx.ASGITransport`:
POST /screen writes a Message + ScreeningResult + a chained ledger entry, and
every read endpoint then computes its numbers from that same stored data. It
proves the whole system except the Groq network call itself.

The LLM is the only thing faked, and only here — `app.llm.client` has no
offline runtime mode by design, so this monkeypatches the router's
`get_llm_client` lookup rather than introducing a config flag that could ever
be switched on in production.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.main import app
from app.ratelimit import screen_limiter

# Marker text the fake client keys off so verdicts are deterministic.
VIOLATION_MARKER = "worthless deadbeat"
HARDSHIP_MARKER = "I lost my job"


class FakeLLM:
    """Deterministic stand-in. Branches on the schema it was handed."""

    def __init__(self) -> None:
        self.calls = 0

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: dict[str, Any],
        model: str,
        max_tokens: int = 800,
    ) -> dict[str, Any]:
        self.calls += 1
        props = schema.get("properties", {})

        if "signals" in props:  # hardship detection
            if HARDSHIP_MARKER in user:
                return {
                    "signals": [
                        {"signal_type": "job_loss", "quoted_text": HARDSHIP_MARKER}
                    ]
                }
            return {"signals": []}

        if "summary" in props:  # coaching summary
            return {"summary": "Repeatedly uses degrading language toward borrowers."}

        # screening
        if VIOLATION_MARKER in user:
            return {
                "violation": True,
                "rule": "R1_ABUSIVE_LANGUAGE",
                "quoted_phrase": VIOLATION_MARKER,
                "explanation": "Degrading characterisation of the borrower.",
                "suggested_rewrite": "Your account is overdue; can we agree a plan?",
            }
        return {
            "violation": False,
            "rule": None,
            "quoted_phrase": None,
            "explanation": "Professional and factual.",
            "suggested_rewrite": None,
        }


@pytest.fixture
async def client(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """The real app, wired to the test session and a fake LLM."""
    await session.run_sync(lambda conn: None)  # ensure the session is live

    fake = FakeLLM()
    monkeypatch.setattr("app.routers.screen.get_llm_client", lambda: fake)
    monkeypatch.setattr("app.routers.coaching.get_llm_client", lambda: fake)

    # The limiter is deliberately process-global, so it carries state between
    # tests. Reset it per test, or whichever test runs second inherits the
    # previous one's request count and 429s for reasons unrelated to itself.
    screen_limiter.reset()

    async def _override_session():
        yield session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _post(ac: AsyncClient, text: str, *, when: dt.datetime, is_customer: bool = False,
                account: str = "4471", channel: str = "whatsapp"):
    resp = await ac.post(
        "/screen",
        json={
            "text": text,
            "channel": channel,
            "account_id": account,
            "is_customer": is_customer,
            "occurred_at": when.isoformat(),
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_full_pipeline_every_screen_is_real_and_every_read_agrees(
    client: AsyncClient,
) -> None:
    base = dt.datetime.now(dt.UTC) - dt.timedelta(days=3)

    # 5 collector contacts inside one hour on account 4471 -> breaches the
    # 3-per-week published limit AND trips the burst heuristic.
    for i in range(5):
        await _post(
            client,
            f"You are a {VIOLATION_MARKER} and everyone should know it. ({i})",
            when=base + dt.timedelta(minutes=i * 10),
        )
    # 3 clean messages on the same account
    for i in range(3):
        await _post(
            client,
            f"Good morning, a reminder about your balance of RM{300 + i}.",
            when=base + dt.timedelta(days=1, hours=i),
        )
    # A customer hardship disclosure
    await _post(
        client,
        f"{HARDSHIP_MARKER} last month and cannot pay right now.",
        when=base + dt.timedelta(days=1, hours=5),
        is_customer=True,
    )
    # A clean message on a second account, so /agencies has more than one row
    await _post(
        client,
        "Your statement is ready to view online.",
        when=base + dt.timedelta(days=2),
        account="9900",
        channel="email",
    )

    # --- /dashboard/stats -------------------------------------------------
    stats = (await client.get("/dashboard/stats")).json()
    # 10 messages posted; the customer one is not screened for conduct, but a
    # ScreeningResult row is still written for it, so all 10 are counted.
    assert stats["total_screened"] == 10
    assert stats["total_violations"] == 5
    assert stats["active_accounts"] == 2
    assert stats["open_hardship_cases"] == 1
    assert abs(stats["violation_rate"] - 0.5) < 1e-9
    assert len(stats["chart"]) == 14

    # --- /timeline/4471 ---------------------------------------------------
    timeline = (await client.get("/timeline/4471")).json()
    assert timeline["message_count"] == 9
    patterns = {p["rule"]: p for p in timeline["patterns"]}

    r5 = patterns["R5_CONTACT_FREQUENCY"]
    assert r5["triggered"] is True
    assert r5["is_published_limit"] is True

    burst = patterns["BURST_HEURISTIC"]
    assert burst["triggered"] is True
    # The heuristic must never be presented as a regulatory limit.
    assert burst["is_published_limit"] is False
    assert "not a published" in burst["label"].lower()

    # --- /ledger and /ledger/verify --------------------------------------
    ledger = (await client.get("/ledger")).json()
    assert ledger["total"] == 10

    verify = (await client.post("/ledger/verify")).json()
    assert verify["valid"] is True
    assert verify["total"] == 10
    assert verify["failed"] == 0
    assert verify["first_broken_id"] is None
    # Every row rehashed to exactly what was stored.
    assert all(row["stored_hash"] == row["computed_hash"] for row in verify["rows"])

    # --- /coaching --------------------------------------------------------
    coaching = (await client.get("/coaching")).json()
    assert coaching["rows"], "expected at least one collector row"
    top = coaching["rows"][0]
    assert top["flagged"] == 5
    assert top["top_rule"] == "R1_ABUSIVE_LANGUAGE"
    assert top["pattern_summary"]

    # Second call must be served from cache — no extra LLM traffic, and the
    # wording must not change between refreshes during a live demo.
    coaching2 = (await client.get("/coaching")).json()
    assert coaching2["cached"] is True
    assert coaching2["rows"][0]["pattern_summary"] == top["pattern_summary"]

    # --- /hardship --------------------------------------------------------
    hardship = (await client.get("/hardship")).json()
    assert hardship["total"] == 1
    assert hardship["rows"][0]["signal_type"] == "job_loss"
    assert hardship["rows"][0]["account_external_id"] == "4471"

    # --- /agencies --------------------------------------------------------
    agencies = (await client.get("/agencies")).json()
    assert agencies["rows"]
    total_violations = sum(r["violations"] for r in agencies["rows"])
    assert total_violations == 5
    for row in agencies["rows"]:
        assert 0.0 <= row["compliance_score"] <= 100.0
        assert row["grade"] in {"A", "B", "C", "D", "F"}


async def test_screen_rejects_oversized_input(client: AsyncClient) -> None:
    resp = await client.post(
        "/screen",
        json={"text": "x" * 5000, "channel": "sms", "account_id": "4471"},
    )
    assert resp.status_code == 413
    assert resp.json()["detail"]["code"] == "message_too_long"


async def test_health_reports_configuration_honestly(client: AsyncClient) -> None:
    """/health must report real configuration state, not a blanket 'ok'.

    Asserted against settings rather than a hardcoded value: a developer with a
    populated .env would otherwise fail this test for no reason, and the actual
    contract is "these flags tell the truth", not "these flags are false".
    """
    from app.config import get_settings

    settings = get_settings()
    body = (await client.get("/health")).json()

    assert body["status"] == "ok"
    assert body["groq_configured"] == bool(settings.groq_api_key)
    assert body["database_configured"] == bool(settings.database_url)
    assert body["model"] == settings.groq_model
