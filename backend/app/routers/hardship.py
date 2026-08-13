"""GET /hardship — customer messages showing genuine hardship signals.

Detection happens on write (in /screen, for customer-side messages), not here.
This endpoint is a pure read so the queue loads instantly during a demo.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Account, HardshipSignal, Message
from app.schemas import HardshipResponse, HardshipRow

router = APIRouter()


@router.get("/hardship", response_model=HardshipResponse)
async def hardship(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=100, ge=1, le=500),
) -> HardshipResponse:
    total = await session.scalar(select(func.count(HardshipSignal.id)))

    result = await session.execute(
        select(HardshipSignal, Message, Account)
        .join(Message, Message.id == HardshipSignal.message_id)
        .join(Account, Account.id == Message.account_id)
        .order_by(HardshipSignal.detected_at.desc())
        .limit(limit)
    )

    rows = [
        HardshipRow(
            id=signal.id,
            message_id=message.id,
            account_external_id=account.external_id,
            signal_type=signal.signal_type,
            quoted_text=signal.quoted_text,
            raw_text=message.raw_text,
            occurred_at=message.occurred_at,
            detected_at=signal.detected_at,
        )
        for signal, message, account in result.all()
    ]

    return HardshipResponse(total=int(total or 0), rows=rows)
