"""User profile API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from cran_code.config import load_config
from cran_code.web.auth_v2.jwt import User as JWTUser
from cran_code.web.auth_v2.jwt import require_admin, require_user
from cran_code.web.db import (
    AsyncSessionLocal,
    TeamMember,
    UsageRecord,
    User,
    UserProviderKey,
    UserRole,
)
from cran_code.web.db.keys import quota_summary
from cran_code.web.db.tz import local_day_start_utc, sqlite_shift_modifier, validate_tz_name

router = APIRouter(prefix="/api/v2/users", tags=["users"])


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)


class UserResponse(BaseModel):
    id: str
    email: str | None
    username: str
    display_name: str | None
    avatar_url: str | None
    role: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: JWTUser = Depends(require_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat(),
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    req: UserProfileUpdate,
    current_user: JWTUser = Depends(require_user),
) -> UserResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one()
        if req.display_name is not None:
            user.display_name = req.display_name
        if req.avatar_url is not None:
            user.avatar_url = req.avatar_url
        await session.commit()
        await session.refresh(user)
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            role=user.role.value,
            created_at=user.created_at.isoformat(),
        )


@router.get("/search", response_model=list[UserResponse])
async def search_users(
    q: str,
    current_user: JWTUser = Depends(require_user),
) -> list[UserResponse]:
    """Search users by username, email, or display_name."""
    async with AsyncSessionLocal() as session:
        query = q.lower()
        result = await session.execute(
            select(User).where(
                (User.username.ilike(f"%{query}%"))
                | (User.email.ilike(f"%{query}%"))
                | (User.display_name.ilike(f"%{query}%"))
            )
        )
        users = result.scalars().all()
        return [
            UserResponse(
                id=u.id,
                email=u.email if u.id == current_user.id else None,
                username=u.username,
                display_name=u.display_name,
                avatar_url=u.avatar_url,
                role=u.role.value,
                created_at=u.created_at.isoformat(),
            )
            for u in users
        ]


class UserRoleUpdate(BaseModel):
    role: str = Field(..., min_length=1)


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: str,
    req: UserRoleUpdate,
    current_user: JWTUser = Depends(require_admin),
) -> UserResponse:
    """Change a user's global role (admin only)."""
    if req.role not in (UserRole.admin.value, UserRole.user.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'admin' or 'user'",
        )
    if user_id == current_user.id and req.role != UserRole.admin.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot demote themselves",
        )
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        user.role = UserRole(req.role)
        await session.commit()
        await session.refresh(user)
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            role=user.role.value,
            created_at=user.created_at.isoformat(),
        )


class ProviderKeyUpsertRequest(BaseModel):
    api_key: str = Field(..., min_length=1, max_length=500)


class ProviderKeyResponse(BaseModel):
    provider_key: str
    has_api_key: bool
    created_at: str | None = None
    updated_at: str | None = None
    # NEVER include key material in responses.


@router.get("/me/provider-keys", response_model=list[ProviderKeyResponse])
async def list_my_provider_keys(
    current_user: JWTUser = Depends(require_user),
) -> list[ProviderKeyResponse]:
    """List the current user's stored provider keys (masked)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserProviderKey).where(UserProviderKey.user_id == current_user.id)
        )
        keys = result.scalars().all()
        return [
            ProviderKeyResponse(
                provider_key=k.provider_key,
                has_api_key=True,
                created_at=k.created_at.isoformat(),
                updated_at=k.updated_at.isoformat(),
            )
            for k in keys
        ]


@router.put("/me/provider-keys/{provider_key}", response_model=ProviderKeyResponse)
async def upsert_my_provider_key(
    provider_key: str,
    req: ProviderKeyUpsertRequest,
    current_user: JWTUser = Depends(require_user),
) -> ProviderKeyResponse:
    """Create or replace the current user's API key for a provider."""
    if provider_key not in load_config().providers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_key}' not found",
        )
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserProviderKey).where(
                UserProviderKey.user_id == current_user.id,
                UserProviderKey.provider_key == provider_key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.api_key = req.api_key
        else:
            session.add(
                UserProviderKey(
                    user_id=current_user.id,
                    provider_key=provider_key,
                    api_key=req.api_key,
                )
            )
        await session.commit()
        return ProviderKeyResponse(provider_key=provider_key, has_api_key=True)


@router.delete("/me/provider-keys/{provider_key}")
async def delete_my_provider_key(
    provider_key: str,
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    """Delete the current user's API key for a provider."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(UserProviderKey).where(
                UserProviderKey.user_id == current_user.id,
                UserProviderKey.provider_key == provider_key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider key not found",
            )
        await session.delete(existing)
        await session.commit()
        return {"detail": "Provider key deleted"}


class UsageSummary(BaseModel):
    provider_key: str
    source: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    quota_tokens: int | None = None
    remaining_tokens: int | None = None


@router.get("/me/usage", response_model=list[UsageSummary])
async def get_my_usage(
    current_user: JWTUser = Depends(require_user),
) -> list[UsageSummary]:
    """Per-provider token usage summary for the current user.

    Rows are grouped by ``(provider_key, source)``. Rows with
    ``source='shared'`` additionally carry ``quota_tokens`` /
    ``remaining_tokens`` when a restricted-mode grant covers the user
    (``None`` = unlimited / not applicable).
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(
                UsageRecord.provider_key,
                UsageRecord.source,
                func.coalesce(func.sum(UsageRecord.input_tokens), 0),
                func.coalesce(func.sum(UsageRecord.output_tokens), 0),
            )
            .where(UsageRecord.user_id == current_user.id)
            .group_by(UsageRecord.provider_key, UsageRecord.source)
        )
        rows = result.all()

        team_result = await session.execute(
            select(TeamMember.team_id).where(TeamMember.user_id == current_user.id)
        )
        team_ids = list(team_result.scalars().all())

    summaries: list[UsageSummary] = []
    for provider_key, source, input_tokens, output_tokens in rows:
        quota: int | None = None
        remaining: int | None = None
        if source == "shared":
            quota, remaining = await quota_summary(
                current_user.id, provider_key, team_ids
            )
        summaries.append(
            UsageSummary(
                provider_key=provider_key,
                source=source,
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
                total_tokens=int(input_tokens) + int(output_tokens),
                quota_tokens=quota,
                remaining_tokens=remaining,
            )
        )
    return summaries


class UsageDailyPoint(BaseModel):
    """One day of aggregated usage for a (provider, model, source) bucket."""

    date: str  # YYYY-MM-DD (UTC)
    provider_key: str
    model: str
    source: str
    input_tokens: int
    output_tokens: int


@router.get("/me/usage/daily", response_model=list[UsageDailyPoint])
async def get_my_usage_daily(
    days: int = 30,
    tz: str | None = None,
    current_user: JWTUser = Depends(require_user),
) -> list[UsageDailyPoint]:
    """Per-day token usage for the current user over the last ``days`` days.

    Rows are grouped by ``(date, provider_key, model, source)`` and ordered
    chronologically. Days are calendar days in the ``tz`` timezone (IANA name,
    default UTC); pass the browser's timezone for a local "today".
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
                UsageRecord.provider_key,
                UsageRecord.model,
                UsageRecord.source,
                func.coalesce(func.sum(UsageRecord.input_tokens), 0),
                func.coalesce(func.sum(UsageRecord.output_tokens), 0),
            )
            .where(
                UsageRecord.user_id == current_user.id,
                UsageRecord.created_at >= since,
            )
            .group_by(
                day_col,
                UsageRecord.provider_key,
                UsageRecord.model,
                UsageRecord.source,
            )
            .order_by(day_col)
        )
        rows = result.all()
    return [
        UsageDailyPoint(
            date=str(date),
            provider_key=provider_key,
            model=model,
            source=source,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
        )
        for date, provider_key, model, source, input_tokens, output_tokens in rows
    ]
