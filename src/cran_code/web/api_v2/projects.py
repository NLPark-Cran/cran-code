"""Project management API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from cran_code.web.auth_v2.jwt import User, require_user
from cran_code.web.db import AsyncSessionLocal, Project, ProjectMember, ProjectMemberRole, TeamMember

router = APIRouter(prefix="/api/v2/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    team_id: str
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    work_dir: str | None = Field(None, max_length=500)
    git_repo_url: str | None = Field(None, max_length=500)
    default_model: str | None = Field(None, max_length=100)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    work_dir: str | None = Field(None, max_length=500)
    git_repo_url: str | None = Field(None, max_length=500)
    default_model: str | None = Field(None, max_length=100)


class ProjectMemberResponse(BaseModel):
    id: str
    user_id: str
    username: str
    display_name: str | None
    role: str
    joined_at: str


class ProjectResponse(BaseModel):
    id: str
    team_id: str
    name: str
    slug: str
    description: str | None
    work_dir: str | None
    git_repo_url: str | None
    default_model: str | None
    created_by: str | None
    members: list[ProjectMemberResponse]
    created_at: str

    class Config:
        from_attributes = True


def _project_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        team_id=project.team_id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        work_dir=project.work_dir,
        git_repo_url=project.git_repo_url,
        default_model=project.default_model,
        created_by=project.created_by,
        members=[
            ProjectMemberResponse(
                id=m.id,
                user_id=m.user_id,
                username=m.user.username,
                display_name=m.user.display_name,
                role=m.role.value,
                joined_at=m.joined_at.isoformat(),
            )
            for m in project.members
        ],
        created_at=project.created_at.isoformat(),
    )


async def _require_team_member(session, team_id: str, user_id: str) -> TeamMember:
    result = await session.execute(
        select(TeamMember).where(
            (TeamMember.team_id == team_id) & (TeamMember.user_id == user_id)
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this team",
        )
    return member


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    team_id: str | None = None,
    current_user: User = Depends(require_user),
) -> list[ProjectResponse]:
    async with AsyncSessionLocal() as session:
        if team_id:
            await _require_team_member(session, team_id, current_user.id)
            result = await session.execute(
                select(Project)
                .where(Project.team_id == team_id)
                .options(selectinload(Project.members).selectinload(ProjectMember.user))
            )
        else:
            # Return all projects the user has access to via team membership
            team_result = await session.execute(
                select(TeamMember).where(TeamMember.user_id == current_user.id)
            )
            team_ids = [m.team_id for m in team_result.scalars().all()]
            result = await session.execute(
                select(Project)
                .where(Project.team_id.in_(team_ids))
                .options(selectinload(Project.members).selectinload(ProjectMember.user))
            )
        projects = result.scalars().all()
        return [_project_response(p) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreate,
    current_user: User = Depends(require_user),
) -> ProjectResponse:
    async with AsyncSessionLocal() as session:
        member = await _require_team_member(session, req.team_id, current_user.id)

        # Check slug uniqueness within team
        existing = await session.execute(
            select(Project).where(
                (Project.team_id == req.team_id) & (Project.slug == req.slug)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project slug already exists in this team",
            )

        project = Project(
            team_id=req.team_id,
            name=req.name,
            slug=req.slug,
            description=req.description,
            work_dir=req.work_dir,
            git_repo_url=req.git_repo_url,
            default_model=req.default_model,
            created_by=current_user.id,
        )
        session.add(project)
        await session.flush()

        # Creator is automatically a member
        membership = ProjectMember(
            project_id=project.id,
            user_id=current_user.id,
            role=ProjectMemberRole.owner,
        )
        session.add(membership)
        await session.commit()
        await session.refresh(project)

        result = await session.execute(
            select(Project)
            .where(Project.id == project.id)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
        )
        project = result.scalar_one()
        return _project_response(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(require_user),
) -> ProjectResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        await _require_team_member(session, project.team_id, current_user.id)
        return _project_response(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    req: ProjectUpdate,
    current_user: User = Depends(require_user),
) -> ProjectResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Project)
            .where(Project.id == project_id)
            .options(selectinload(Project.members).selectinload(ProjectMember.user))
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        # Require admin+ on project
        member_result = await session.execute(
            select(ProjectMember).where(
                (ProjectMember.project_id == project_id)
                & (ProjectMember.user_id == current_user.id)
            )
        )
        membership = member_result.scalar_one_or_none()
        if membership is None or membership.role not in (
            ProjectMemberRole.owner,
            ProjectMemberRole.admin,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        if req.name is not None:
            project.name = req.name
        if req.description is not None:
            project.description = req.description
        if req.work_dir is not None:
            project.work_dir = req.work_dir
        if req.git_repo_url is not None:
            project.git_repo_url = req.git_repo_url
        if req.default_model is not None:
            project.default_model = req.default_model
        await session.commit()
        await session.refresh(project)
        return _project_response(project)
