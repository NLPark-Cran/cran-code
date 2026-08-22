"""Team management API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from cran_code.config import load_config
from cran_code.web.auth_v2.jwt import User as JWTUser
from cran_code.web.auth_v2.jwt import require_user
from cran_code.web.db import (
    AsyncSessionLocal,
    Team,
    TeamMember,
    TeamMemberRole,
    TeamProviderKey,
    User,
)
from cran_code.web.db.tz import validate_tz_name

router = APIRouter(prefix="/api/v2/teams", tags=["teams"])


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class TeamUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    timezone: str | None = Field(
        None,
        max_length=64,
        description="IANA display timezone for team usage statistics (e.g. Asia/Shanghai). "
        "Empty string clears it back to UTC.",
    )


class TeamMemberResponse(BaseModel):
    id: str
    user_id: str
    username: str
    display_name: str | None
    role: str
    joined_at: str


class TeamResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None
    timezone: str | None
    owner_id: str
    members: list[TeamMemberResponse]
    created_at: str

    class Config:
        from_attributes = True


def _team_response(team: Team) -> TeamResponse:
    return TeamResponse(
        id=team.id,
        name=team.name,
        slug=team.slug,
        description=team.description,
        timezone=team.timezone,
        owner_id=team.owner_id,
        members=[
            TeamMemberResponse(
                id=m.id,
                user_id=m.user_id,
                username=m.user.username,
                display_name=m.user.display_name,
                role=m.role.value,
                joined_at=m.joined_at.isoformat(),
            )
            for m in team.members
        ],
        created_at=team.created_at.isoformat(),
    )


@router.get("", response_model=list[TeamResponse])
async def list_teams(current_user: JWTUser = Depends(require_user)) -> list[TeamResponse]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Team)
            .where(Team.owner_id == current_user.id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        owned = result.scalars().all()

        result2 = await session.execute(
            select(TeamMember)
            .where(TeamMember.user_id == current_user.id)
            .options(selectinload(TeamMember.team).selectinload(Team.members).selectinload(TeamMember.user))
        )
        member_of = [m.team for m in result2.scalars().all()]

        # Deduplicate and return
        seen = {t.id for t in owned}
        all_teams = list(owned)
        for t in member_of:
            if t.id not in seen:
                all_teams.append(t)
                seen.add(t.id)
        return [_team_response(t) for t in all_teams]


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    req: TeamCreate,
    current_user: JWTUser = Depends(require_user),
) -> TeamResponse:
    async with AsyncSessionLocal() as session:
        # Check slug uniqueness
        existing = await session.execute(select(Team).where(Team.slug == req.slug))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Team slug already exists",
            )

        team = Team(
            name=req.name,
            slug=req.slug,
            description=req.description,
            owner_id=current_user.id,
        )
        session.add(team)
        await session.flush()

        # Owner is automatically a member
        membership = TeamMember(
            team_id=team.id,
            user_id=current_user.id,
            role=TeamMemberRole.owner,
        )
        session.add(membership)
        await session.commit()
        await session.refresh(team)

        # Reload with relationships
        result = await session.execute(
            select(Team)
            .where(Team.id == team.id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        team = result.scalar_one()
        return _team_response(team)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: str,
    current_user: JWTUser = Depends(require_user),
) -> TeamResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        team = result.scalar_one_or_none()
        if team is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

        # Check membership
        member_result = await session.execute(
            select(TeamMember).where(
                (TeamMember.team_id == team_id) & (TeamMember.user_id == current_user.id)
            )
        )
        if member_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a team member")

        return _team_response(team)


@router.patch("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    req: TeamUpdate,
    current_user: JWTUser = Depends(require_user),
) -> TeamResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        team = result.scalar_one_or_none()
        if team is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

        # Only owner or admin can update
        member_result = await session.execute(
            select(TeamMember).where(
                (TeamMember.team_id == team_id) & (TeamMember.user_id == current_user.id)
            )
        )
        membership = member_result.scalar_one_or_none()
        if membership is None or membership.role not in (
            TeamMemberRole.owner,
            TeamMemberRole.admin,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        if req.name is not None:
            team.name = req.name
        if req.description is not None:
            team.description = req.description
        if req.timezone is not None:
            if req.timezone == "":
                team.timezone = None
            else:
                try:
                    validate_tz_name(req.timezone)
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
                    ) from exc
                team.timezone = req.timezone
        await session.commit()
        await session.refresh(team)
        return _team_response(team)


class TeamMemberUpdateRole(BaseModel):
    role: str = Field(..., pattern="^(owner|admin|member)$")


@router.post("/{team_id}/members", response_model=TeamResponse)
async def add_team_member(
    team_id: str,
    user_id: str,
    role: str = "member",
    current_user: JWTUser = Depends(require_user),
) -> TeamResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        team = result.scalar_one_or_none()
        if team is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

        # Only owner or admin can add members
        member_result = await session.execute(
            select(TeamMember).where(
                (TeamMember.team_id == team_id) & (TeamMember.user_id == current_user.id)
            )
        )
        membership = member_result.scalar_one_or_none()
        if membership is None or membership.role not in (
            TeamMemberRole.owner,
            TeamMemberRole.admin,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        # Check target user exists
        user_result = await session.execute(select(User).where(User.id == user_id))
        if user_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Check not already a member
        existing = await session.execute(
            select(TeamMember).where(
                (TeamMember.team_id == team_id) & (TeamMember.user_id == user_id)
            )
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a team member",
            )

        if TeamMemberRole(role) == TeamMemberRole.owner and membership.role != TeamMemberRole.owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owner can assign owner role",
            )

        new_member = TeamMember(
            team_id=team_id,
            user_id=user_id,
            role=TeamMemberRole(role),
        )
        session.add(new_member)
        await session.commit()
        # Re-fetch with eager-loaded relationships after commit
        result = await session.execute(
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        team = result.scalar_one()
        return _team_response(team)


@router.patch("/{team_id}/members/{member_id}", response_model=TeamResponse)
async def update_team_member_role(
    team_id: str,
    member_id: str,
    req: TeamMemberUpdateRole,
    current_user: JWTUser = Depends(require_user),
) -> TeamResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        team = result.scalar_one_or_none()
        if team is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

        # Only owner or admin can change roles
        actor_result = await session.execute(
            select(TeamMember).where(
                (TeamMember.team_id == team_id) & (TeamMember.user_id == current_user.id)
            )
        )
        actor = actor_result.scalar_one_or_none()
        if actor is None or actor.role not in (TeamMemberRole.owner, TeamMemberRole.admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        target_result = await session.execute(
            select(TeamMember).where(
                (TeamMember.id == member_id) & (TeamMember.team_id == team_id)
            )
        )
        target = target_result.scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        # Only owner can assign owner role; admin cannot modify owner
        if req.role == "owner" and actor.role != TeamMemberRole.owner:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can assign owner role")
        if target.role == TeamMemberRole.owner and actor.role != TeamMemberRole.owner:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can modify owner")

        target.role = TeamMemberRole(req.role)
        await session.commit()
        # Re-fetch with eager-loaded relationships after commit
        result = await session.execute(
            select(Team)
            .where(Team.id == team_id)
            .options(selectinload(Team.members).selectinload(TeamMember.user))
        )
        team = result.scalar_one()
        return _team_response(team)


@router.delete("/{team_id}/members/{member_id}")
async def remove_team_member(
    team_id: str,
    member_id: str,
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if team is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

        actor_result = await session.execute(
            select(TeamMember).where(
                (TeamMember.team_id == team_id) & (TeamMember.user_id == current_user.id)
            )
        )
        actor = actor_result.scalar_one_or_none()

        target_result = await session.execute(
            select(TeamMember).where(
                (TeamMember.id == member_id) & (TeamMember.team_id == team_id)
            )
        )
        target = target_result.scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

        # Users can remove themselves; owner/admin can remove others
        # Owner cannot be removed except by themselves
        can_remove = (
            target.user_id == current_user.id
            or (actor is not None and actor.role in (TeamMemberRole.owner, TeamMemberRole.admin))
        )
        if target.role == TeamMemberRole.owner and target.user_id != current_user.id:
            can_remove = False
        if not can_remove:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

        # Prevent removing the last owner
        if target.role == TeamMemberRole.owner:
            owner_count_result = await session.execute(
                select(func.count(TeamMember.id)).where(
                    (TeamMember.team_id == team_id)
                    & (TeamMember.role == TeamMemberRole.owner)
                )
            )
            owner_count = owner_count_result.scalar()
            if owner_count is None or owner_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the last owner",
                )

        await session.delete(target)
        await session.commit()
        return {"detail": "Member removed"}


class TeamProviderKeyUpsertRequest(BaseModel):
    api_key: str = Field(..., min_length=1, max_length=500)


class TeamProviderKeyResponse(BaseModel):
    provider_key: str
    has_api_key: bool
    # NEVER include key material in responses.


async def _require_team_admin(
    session: AsyncSession, team_id: str, user_id: str
) -> TeamMember:
    """Resolve the caller's membership, requiring team owner/admin role."""
    team = await session.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    member_result = await session.execute(
        select(TeamMember).where(
            (TeamMember.team_id == team_id) & (TeamMember.user_id == user_id)
        )
    )
    membership = member_result.scalar_one_or_none()
    if membership is None or membership.role not in (
        TeamMemberRole.owner,
        TeamMemberRole.admin,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )
    return membership


@router.get("/{team_id}/provider-keys", response_model=list[TeamProviderKeyResponse])
async def list_team_provider_keys(
    team_id: str,
    current_user: JWTUser = Depends(require_user),
) -> list[TeamProviderKeyResponse]:
    """List a team's stored provider keys (masked). Team owner/admin only."""
    async with AsyncSessionLocal() as session:
        await _require_team_admin(session, team_id, current_user.id)
        result = await session.execute(
            select(TeamProviderKey).where(TeamProviderKey.team_id == team_id)
        )
        keys = result.scalars().all()
        return [
            TeamProviderKeyResponse(provider_key=k.provider_key, has_api_key=True)
            for k in keys
        ]


@router.put("/{team_id}/provider-keys/{provider_key}", response_model=TeamProviderKeyResponse)
async def upsert_team_provider_key(
    team_id: str,
    provider_key: str,
    req: TeamProviderKeyUpsertRequest,
    current_user: JWTUser = Depends(require_user),
) -> TeamProviderKeyResponse:
    """Create or replace a team's API key for a provider. Team owner/admin only."""
    if provider_key not in load_config().providers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_key}' not found",
        )
    async with AsyncSessionLocal() as session:
        await _require_team_admin(session, team_id, current_user.id)
        result = await session.execute(
            select(TeamProviderKey).where(
                TeamProviderKey.team_id == team_id,
                TeamProviderKey.provider_key == provider_key,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            existing.api_key = req.api_key
        else:
            session.add(
                TeamProviderKey(
                    team_id=team_id,
                    provider_key=provider_key,
                    api_key=req.api_key,
                )
            )
        await session.commit()
        return TeamProviderKeyResponse(provider_key=provider_key, has_api_key=True)


@router.delete("/{team_id}/provider-keys/{provider_key}")
async def delete_team_provider_key(
    team_id: str,
    provider_key: str,
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    """Delete a team's API key for a provider. Team owner/admin only."""
    async with AsyncSessionLocal() as session:
        await _require_team_admin(session, team_id, current_user.id)
        result = await session.execute(
            select(TeamProviderKey).where(
                TeamProviderKey.team_id == team_id,
                TeamProviderKey.provider_key == provider_key,
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
