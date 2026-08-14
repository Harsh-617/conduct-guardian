"""Agency compliance leaderboard — computed on read, never stored."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Agency, Message, ScreeningResult
from app.schemas import AgencyResponse, AgencyRow

router = APIRouter()


@router.get("/agencies", response_model=AgencyResponse)
async def list_agencies(session: AsyncSession = Depends(get_session)) -> AgencyResponse:
    """Agencies ranked by compliance score, computed from their real screening results."""
    # The denominator is SCREENED messages, not all messages. Customer-side
    # messages are never screened, so counting them would make an agency's
    # score depend on how much its borrowers reply — a chatty customer base
    # would silently improve the compliance grade.
    stmt = (
        select(
            Agency.id,
            Agency.name,
            func.count(func.distinct(Message.id)).label("total_messages"),
            func.count(func.distinct(ScreeningResult.message_id)).label("screened"),
            func.count(
                func.distinct(case((ScreeningResult.violation.is_(True), Message.id)))
            ).label("violations"),
        )
        .select_from(Agency)
        .outerjoin(Message, Message.agency_id == Agency.id)
        .outerjoin(ScreeningResult, ScreeningResult.message_id == Message.id)
        .group_by(Agency.id, Agency.name)
    )
    rows = (await session.execute(stmt)).all()

    agency_rows = [
        _to_agency_row(agency_id, name, total, screened, violations)
        for agency_id, name, total, screened, violations in rows
    ]
    agency_rows.sort(key=lambda row: row.compliance_score, reverse=True)

    return AgencyResponse(rows=agency_rows)


def _to_agency_row(
    agency_id: int, name: str, total: int, screened: int, violations: int
) -> AgencyRow:
    total = total or 0
    screened = screened or 0
    violations = violations or 0
    # No screened messages means no evidence either way — score 100 rather than
    # inventing a penalty for an agency we simply have no data on.
    compliance_score = (
        100.0 if screened == 0 else round(100 * (1 - violations / screened), 1)
    )
    return AgencyRow(
        agency_id=agency_id,
        name=name,
        total_messages=total,
        violations=violations,
        compliance_score=compliance_score,
        grade=_grade(compliance_score),
    )


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"
