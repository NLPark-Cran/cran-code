"""Admin-only API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from cran_code.web.auth_v2.jwt import User as JWTUser
from cran_code.web.auth_v2.jwt import require_admin
from cran_code.web.db import AsyncSessionLocal, UsageRecord, User
from cran_code.web.db.tz import local_day_start_utc, sqlite_shift_modifier, validate_tz_name

router = APIRouter(prefix="/api/v2/admin", tags=["admin"])


class AdminUsageDailyPoint(BaseModel):
    """One day of aggregated usage for a (user, provider, model, source) bucket."""

    date: str  # YYYY-MM-DD (UTC)
    user_id: str
    username: str
    provider_key: str
    model: str
    source: str
    input_tokens: int
    output_tokens: int


@router.get("/usage", response_model=list[AdminUsageDailyPoint])
async def get_admin_usage(
    days: int = 30,
    tz: str | None = None,
    current_user: JWTUser = Depends(require_admin),
) -> list[AdminUsageDailyPoint]:
    """Per-day token usage for ALL users (admin only).

    Same bucketing as ``/users/me/usage/daily`` but additionally grouped by
    user, with ``username`` resolved via a join. Ordered by date, then user.
    Days are calendar days in the ``tz`` timezone (IANA name, default UTC).
    ``days`` is clamped to [1, 90].
    """
    days = min(max(days, 1), 90)
    if tz is not None:
        try:
            validate_tz_name(tz)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    since = local_day_start_utc(tz, days)
    day_col = func.date(func.datetime(UsageRecord.created_at, sqlite_shift_modifier(tz)))
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                day_col,
                UsageRecord.user_id,
                User.username,
                UsageRecord.provider_key,
                UsageRecord.model,
                UsageRecord.source,
                func.coalesce(func.sum(UsageRecord.input_tokens), 0),
                func.coalesce(func.sum(UsageRecord.output_tokens), 0),
            )
            .join(User, User.id == UsageRecord.user_id)
            .where(UsageRecord.created_at >= since)
            .group_by(
                day_col,
                UsageRecord.user_id,
                User.username,
                UsageRecord.provider_key,
                UsageRecord.model,
                UsageRecord.source,
            )
            .order_by(day_col, UsageRecord.user_id)
        )
        rows = result.all()
    return [
        AdminUsageDailyPoint(
            date=str(date),
            user_id=user_id,
            username=username,
            provider_key=provider_key,
            model=model,
            source=source,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
        )
        for (
            date,
            user_id,
            username,
            provider_key,
            model,
            source,
            input_tokens,
            output_tokens,
        ) in rows
    ]
