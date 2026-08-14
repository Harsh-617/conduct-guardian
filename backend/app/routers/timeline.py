"""Per-account cross-channel timeline, with computed contact-pattern flags."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import rules
from app.db import get_session
from app.models import Account, Collector, Message, ScreeningResult
from app.schemas import ErrorBody, PatternFlag, TimelineMessage, TimelineResponse

router = APIRouter()


@router.get("/timeline/{account_id}", response_model=TimelineResponse)
async def get_timeline(
    account_id: str,
    session: AsyncSession = Depends(get_session),
) -> TimelineResponse:
    """All messages for `account_id` (an Account.external_id), every channel, chronological."""
    account = (
        await session.execute(select(Account).where(Account.external_id == account_id))
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="account_not_found",
                message=f"No account with external_id '{account_id}'.",
                retryable=False,
            ).model_dump(),
        )

    # Inner join to Collector (every message has one); outer join to
    # ScreeningResult since customer-side messages are never screened.
    stmt = (
        select(Message, Collector.name, ScreeningResult)
        .join(Collector, Collector.id == Message.collector_id)
        .outerjoin(ScreeningResult, ScreeningResult.message_id == Message.id)
        .where(Message.account_id == account.id)
        .order_by(Message.occurred_at.asc())
    )
    rows = (await session.execute(stmt)).all()

    messages = [
        TimelineMessage(
            id=message.id,
            channel=message.channel,
            raw_text=message.raw_text,
            is_customer=message.is_customer,
            occurred_at=message.occurred_at,
            collector_name=collector_name,
            violation=screening.violation if screening else None,
            rule=screening.rule if screening else None,
            quoted_phrase=screening.quoted_phrase if screening else None,
        )
        for message, collector_name, screening in rows
    ]

    patterns = [_contact_frequency_flag(messages), _burst_flag(messages)]

    return TimelineResponse(
        account_external_id=account.external_id,
        message_count=len(messages),
        messages=messages,
        patterns=patterns,
    )


def _collector_contact_times(messages: list[TimelineMessage]) -> list[dt.datetime]:
    """Chronological occurred_at for collector -> customer messages only."""
    return sorted(m.occurred_at for m in messages if not m.is_customer)


def _worst_window(
    times: list[dt.datetime], span: dt.timedelta
) -> tuple[int, dt.datetime | None, dt.datetime | None]:
    """Slide a window of length `span` over sorted `times`; return the densest window.

    Two-pointer scan over the already-sorted list: `left` only advances when the
    span between `left` and `right` exceeds `span`, so this is O(n) rather than
    checking every pair of timestamps.
    """
    best_count = 0
    best_start: dt.datetime | None = None
    best_end: dt.datetime | None = None
    left = 0
    for right in range(len(times)):
        while times[right] - times[left] > span:
            left += 1
        count = right - left + 1
        if count > best_count:
            best_count = count
            best_start = times[left]
            best_end = times[right]
    return best_count, best_start, best_end


def _contact_frequency_flag(messages: list[TimelineMessage]) -> PatternFlag:
    """R5: any rolling 7-day window with more than the published weekly limit."""
    times = _collector_contact_times(messages)
    count, start, end = _worst_window(times, dt.timedelta(days=7))
    label = f"Exceeds BNM limit of {rules.MAX_CONTACTS_PER_WEEK} contacts per week"
    if start is None:
        detail = "No collector contacts recorded."
    else:
        detail = (
            f"Worst 7-day window: {count} contacts between "
            f"{start.isoformat()} and {end.isoformat()}"
        )
    return PatternFlag(
        triggered=count > rules.MAX_CONTACTS_PER_WEEK,
        rule="R5_CONTACT_FREQUENCY",
        label=label,
        detail=detail,
        is_published_limit=True,
    )


def _burst_flag(messages: list[TimelineMessage]) -> PatternFlag:
    """Internal harassment heuristic — NOT a published regulatory limit."""
    times = _collector_contact_times(messages)
    span = dt.timedelta(minutes=rules.BURST_WINDOW_MINUTES)
    count, start, end = _worst_window(times, span)
    label = (
        f"Internal heuristic, not a published regulatory limit: "
        f"{rules.BURST_CONTACT_COUNT}+ contacts within "
        f"{rules.BURST_WINDOW_MINUTES} minutes"
    )
    if start is None:
        detail = "No collector contacts recorded."
    else:
        detail = (
            f"Worst {rules.BURST_WINDOW_MINUTES}-minute window: {count} contacts "
            f"between {start.isoformat()} and {end.isoformat()}"
        )
    return PatternFlag(
        triggered=count >= rules.BURST_CONTACT_COUNT,
        rule="BURST_HEURISTIC",
        label=label,
        detail=detail,
        is_published_limit=False,
    )
