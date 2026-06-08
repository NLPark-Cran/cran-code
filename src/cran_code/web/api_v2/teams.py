"""Team management API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from cran_code.web.auth_v2.jwt import User, require_user
from cran_code.web.db import AsyncSessionLocal, Team, TeamMember, TeamMemberRole

router = APIRouter(prefix="/api/v2/teams", tags=["teams"])


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


class TeamUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)


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
async def list_teams(current_user: User = Depends(require_user)) -> list[TeamResponse]:
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
    current_user: User = Depends(require_user),
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
    current_user: User = Depends(require_user),
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
    current_user: User = Depends(require_user),
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
        await session.commit()
        await session.refresh(team)
        return _team_response(team)
