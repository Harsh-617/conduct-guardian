"""Lightweight account directory — just enough to populate a lookup picker."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Account
from app.schemas import AccountsResponse

router = APIRouter()


@router.get("/accounts", response_model=AccountsResponse)
async def list_accounts(
    session: AsyncSession = Depends(get_session),
) -> AccountsResponse:
    """All known accounts, id + external_id only, oldest first."""
    accounts = (
        (await session.execute(select(Account).order_by(Account.created_at.asc())))
        .scalars()
        .all()
    )
    return AccountsResponse(accounts=list(accounts))
