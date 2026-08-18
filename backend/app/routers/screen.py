"""POST /screen — the one real pipeline.

message in → Groq screens it → Message + ScreeningResult + chained ledger entry
→ verdict out. Live Screening in the UI and the bulk seeder both go through
here, which is the PRD's core credibility claim: no screen is independently
faked, and the seeded database contains genuine model verdicts.
"""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.ledger import append_entry
from app.llm.client import LLMUnavailable, get_llm_client
from app.llm.hardship import detect_hardship
from app.llm.screening import screen_message
from app.models import Account, Agency, Collector, HardshipSignal, Message, ScreeningResult
from app.ratelimit import rate_limit_screen
from app.schemas import ScreenRequest, ScreenResponse, Verdict

router = APIRouter()


async def _resolve_account(session: AsyncSession, external_id: str) -> Account:
    """Find the account, creating it on first sight.

    Live Screening lets a judge type any account reference; refusing an unknown
    one would break the demo for no benefit on synthetic data.
    """
    found = await session.execute(
        select(Account).where(Account.external_id == external_id)
    )
    account = found.scalars().first()
    if account is None:
        account = Account(external_id=external_id)
        session.add(account)
        await session.flush()
    return account


async def _first_or_create_collector(session: AsyncSession, collector_id: int | None) -> Collector:
    if collector_id is not None:
        found = await session.get(Collector, collector_id)
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "collector_not_found", "message": "Unknown collector_id", "retryable": False},
            )
        return found

    found = await session.execute(select(Collector).order_by(Collector.id).limit(1))
    collector = found.scalars().first()
    if collector is None:
        collector = Collector(name="Live Screening", role="demo")
        session.add(collector)
        await session.flush()
    return collector


async def _first_or_create_agency(session: AsyncSession, agency_id: int | None) -> Agency:
    if agency_id is not None:
        found = await session.get(Agency, agency_id)
        if found is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "agency_not_found", "message": "Unknown agency_id", "retryable": False},
            )
        return found

    found = await session.execute(select(Agency).order_by(Agency.id).limit(1))
    agency = found.scalars().first()
    if agency is None:
        agency = Agency(name="Live Demo Agency")
        session.add(agency)
        await session.flush()
    return agency


@router.post("/screen", response_model=ScreenResponse)
async def screen(
    payload: ScreenRequest,
    session: AsyncSession = Depends(get_session),
    _: None = Depends(rate_limit_screen),
) -> ScreenResponse:
    settings = get_settings()

    text = payload.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "empty_message", "message": "Message text is empty", "retryable": False},
        )
    if len(text) > settings.max_message_chars:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail={
                "code": "message_too_long",
                "message": f"Message exceeds {settings.max_message_chars} characters",
                "retryable": False,
            },
        )

    # Live screening runs on openai/gpt-oss-20b: golden-set data showed it is
    # both faster (6.3s vs 7.7s p50) and more accurate (95.2% vs 90.0% F1)
    # than gpt-oss-120b on this task — see docs/JUDGE-ONEPAGER.md. Bulk
    # seeding uses gpt-oss-120b instead, so a seed run's token spend doesn't
    # eat into the per-minute budget the live demo needs, and every verdict
    # records which model produced it.
    model_used = settings.groq_model_bulk if payload.use_bulk_model else settings.groq_model

    try:
        client = get_llm_client()
    except LLMUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": exc.code, "message": str(exc), "retryable": exc.retryable},
        ) from exc

    account = await _resolve_account(session, payload.account_id)
    collector = await _first_or_create_collector(session, payload.collector_id)
    agency = await _first_or_create_agency(session, payload.agency_id)

    message = Message(
        account_id=account.id,
        collector_id=collector.id,
        agency_id=agency.id,
        channel=payload.channel,
        raw_text=text,
        is_customer=payload.is_customer,
        occurred_at=payload.occurred_at or dt.datetime.now(dt.UTC),
    )
    session.add(message)
    await session.flush()

    # Customer-side text is never screened for collector conduct — it's the
    # borrower speaking. It goes down the hardship path instead.
    if payload.is_customer:
        verdict = Verdict(
            violation=False,
            rule=None,
            quoted_phrase=None,
            explanation="Customer-side message; not screened for collector conduct.",
            suggested_rewrite=None,
        )
        latency_ms = 0
        try:
            signals = await detect_hardship(client, text, model=model_used)
            for signal_type, quoted in signals:
                session.add(
                    HardshipSignal(
                        message_id=message.id, signal_type=signal_type, quoted_text=quoted
                    )
                )
        except LLMUnavailable:
            # A hardship-detection failure must not lose the message itself.
            pass
    else:
        try:
            verdict, latency_ms = await screen_message(
                client, text, model=model_used
            )
        except LLMUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"code": exc.code, "message": str(exc), "retryable": exc.retryable},
            ) from exc

    result = ScreeningResult(
        message_id=message.id,
        violation=verdict.violation,
        rule=verdict.rule,
        quoted_phrase=verdict.quoted_phrase,
        explanation=verdict.explanation,
        suggested_rewrite=verdict.suggested_rewrite,
        model=model_used,
        latency_ms=latency_ms,
    )
    session.add(result)
    # created_at is a server default, so it must exist before it can be hashed.
    await session.flush()
    await session.refresh(result, ["created_at"])

    entry = await append_entry(session, result)
    await session.commit()

    return ScreenResponse(
        message_id=message.id,
        screening_result_id=result.id,
        verdict=verdict,
        model=model_used,
        latency_ms=latency_ms,
        ledger_entry_hash=entry.entry_hash,
    )
