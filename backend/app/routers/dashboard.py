"""Dashboard aggregate stats — read-only rollups over screened messages."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import HardshipSignal, Message, ScreeningResult
from app.schemas import DashboardPoint, DashboardStats

router = APIRouter()

#: Chart window length, in calendar days (inclusive of today).
CHART_DAYS = 14


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session),
) -> DashboardStats:
    """Stat-card numbers plus a 14-day activity chart, computed from stored data."""
    total_screened = (
        await session.execute(select(func.count()).select_from(ScreeningResult))
    ).scalar_one()

    total_violations = (
        await session.execute(
            select(func.count())
            .select_from(ScreeningResult)
            .where(ScreeningResult.violation.is_(True))
        )
    ).scalar_one()

    violation_rate = total_violations / total_screened if total_screened else 0.0

    active_accounts = (
        await session.execute(select(func.count(func.distinct(Message.account_id))))
    ).scalar_one()

    open_hardship_cases = (
        await session.execute(
            select(func.count(func.distinct(HardshipSignal.message_id)))
        )
    ).scalar_one()

    chart = await _build_chart(session)

    return DashboardStats(
        total_screened=total_screened,
        total_violations=total_violations,
        violation_rate=violation_rate,
        active_accounts=active_accounts,
        open_hardship_cases=open_hardship_cases,
        chart=chart,
    )


async def _build_chart(session: AsyncSession) -> list[DashboardPoint]:
    """Last CHART_DAYS calendar days, zero-filled for days with no activity.

    One grouped query, not one query per day: the date range is generated in
    Python and left-filled from a single query result keyed by day.
    """
    today = dt.datetime.now(dt.UTC).date()
    start_date = today - dt.timedelta(days=CHART_DAYS - 1)

    # func.date(...) buckets by calendar day on both Postgres and SQLite.
    day_expr = func.date(Message.occurred_at)
    stmt = (
        select(
            day_expr.label("day"),
            func.count(ScreeningResult.id).label("screened"),
            func.sum(case((ScreeningResult.violation.is_(True), 1), else_=0)).label(
                "violations"
            ),
        )
        .select_from(ScreeningResult)
        .join(Message, Message.id == ScreeningResult.message_id)
        .where(day_expr >= start_date)
        .group_by(day_expr)
    )
    rows = (await session.execute(stmt)).all()

    # The day bucket comes back as a `date` on Postgres/psycopg but as a plain
    # 'YYYY-MM-DD' string on SQLite — normalise both to an ISO key.
    by_day: dict[str, tuple[int, int]] = {}
    for day_value, screened, violations in rows:
        key = (
            day_value.isoformat()
            if isinstance(day_value, dt.date)
            else str(day_value)[:10]
        )
        by_day[key] = (screened, int(violations or 0))

    chart: list[DashboardPoint] = []
    for offset in range(CHART_DAYS):
        day = start_date + dt.timedelta(days=offset)
        screened, violations = by_day.get(day.isoformat(), (0, 0))
        chart.append(DashboardPoint(date=day, screened=screened, violations=violations))
    return chart
