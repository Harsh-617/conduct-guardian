"""Evidence ledger read + integrity-verification endpoints."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ledger import verify_chain
from app.models import Account, EvidenceLedgerEntry, Message, ScreeningResult
from app.schemas import LedgerEntryOut, LedgerPage, VerifyResponse, VerifyRow

router = APIRouter()

MAX_PAGE_SIZE = 100


@router.get("/ledger", response_model=LedgerPage)
async def list_ledger(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    violations_only: bool = Query(
        False,
        description="Return only entries attesting a violation. Used by the dashboard's Recent Flags panel.",
    ),
    session: AsyncSession = Depends(get_session),
) -> LedgerPage:
    """Paginated ledger entries, newest first, with the rule/violation each attests.

    `violations_only` exists because the dashboard's "Recent Flags" panel is
    exactly that — flags. Filtering the newest N client-side would be wrong as
    well as wasteful: if the last five entries happen to be clean you get an
    empty "Recent Flags" list while violations sit one row below the cutoff.
    """
    page_size = min(page_size, MAX_PAGE_SIZE)

    count_stmt = select(func.count()).select_from(EvidenceLedgerEntry)
    if violations_only:
        count_stmt = count_stmt.join(
            ScreeningResult,
            ScreeningResult.id == EvidenceLedgerEntry.screening_result_id,
        ).where(ScreeningResult.violation.is_(True))
    total = (await session.execute(count_stmt)).scalar_one()

    # Joined through to the attested message so the ledger shows WHAT was said,
    # not just that something was hashed. The join is on the same FK chain the
    # hash already covers, so it adds context without weakening the attestation.
    stmt = (
        select(
            EvidenceLedgerEntry,
            ScreeningResult.rule,
            ScreeningResult.violation,
            Message.raw_text,
            Message.channel,
            Message.occurred_at,
            Account.external_id,
        )
        .join(
            ScreeningResult,
            ScreeningResult.id == EvidenceLedgerEntry.screening_result_id,
        )
        .join(Message, Message.id == ScreeningResult.message_id)
        .join(Account, Account.id == Message.account_id)
        .order_by(EvidenceLedgerEntry.id.desc())
    )
    if violations_only:
        stmt = stmt.where(ScreeningResult.violation.is_(True))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).all()

    entries = [
        LedgerEntryOut(
            id=entry.id,
            screening_result_id=entry.screening_result_id,
            entry_hash=entry.entry_hash,
            prev_hash=entry.prev_hash,
            created_at=entry.created_at,
            rule=rule,
            violation=violation,
            account_external_id=external_id,
            channel=channel,
            # Truncated server-side: the table shows a preview, and shipping
            # full message bodies for every page costs bandwidth for text that
            # gets ellipsised in the browser anyway.
            snippet=raw_text if len(raw_text) <= 160 else raw_text[:159] + "…",
            occurred_at=occurred_at,
        )
        for entry, rule, violation, raw_text, channel, occurred_at, external_id in rows
    ]

    return LedgerPage(total=total, page=page, page_size=page_size, entries=entries)


@router.post("/ledger/verify", response_model=VerifyResponse)
async def verify_ledger(session: AsyncSession = Depends(get_session)) -> VerifyResponse:
    """Recompute every hash from stored payloads and compare to what's stored."""
    verdict = await verify_chain(session)
    rows = [
        VerifyRow(
            id=row.id,
            screening_result_id=row.screening_result_id,
            stored_hash=row.stored_hash,
            computed_hash=row.computed_hash,
            ok=row.ok,
            reason=row.reason,
        )
        for row in verdict.rows
    ]
    return VerifyResponse(
        valid=verdict.valid,
        total=verdict.total,
        failed=verdict.failed,
        first_broken_id=verdict.first_broken_id,
        verified_at=dt.datetime.now(dt.UTC),
        rows=rows,
    )
