"""Filesystem access API for IDE integration."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from cran_code.web.auth_v2.jwt import User as JWTUser, require_user
from cran_code.web.db import AsyncSessionLocal, Project, TeamMember

router = APIRouter(prefix="/api/v2/projects", tags=["fs"])


class FsEntry(BaseModel):
    name: str
    path: str
    type: str  # "file" | "directory"
    size: int | None = None


class FsListResponse(BaseModel):
    entries: list[FsEntry]


class FsReadResponse(BaseModel):
    content: str
    path: str


class FsWriteRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=2000)
    content: str


async def _resolve_project_dir(project_id: str, user_id: str) -> Path:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

        team_member = await session.execute(
            select(TeamMember).where(
                (TeamMember.team_id == project.team_id) & (TeamMember.user_id == user_id)
            )
        )
        if team_member.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a team member")

        if not project.work_dir:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project has no working directory",
            )

        work_dir = Path(project.work_dir).expanduser().resolve()
        if not work_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Working directory does not exist",
            )
        return work_dir


def _resolve_path(work_dir: Path, rel_path: str) -> Path:
    """Resolve a path relative to work_dir, preventing directory traversal."""
    target = (work_dir / rel_path.lstrip("/")).resolve()
    # Security: ensure target is inside work_dir
    try:
        target.relative_to(work_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid path: directory traversal detected",
        )
    return target


@router.get("/{project_id}/fs")
async def read_fs(
    project_id: str,
    path: str = "",
    current_user: JWTUser = Depends(require_user),
) -> FsListResponse | FsReadResponse:
    work_dir = await _resolve_project_dir(project_id, current_user.id)
    target = _resolve_path(work_dir, path)

    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not found")

    if target.is_dir():
        entries: list[FsEntry] = []
        try:
            for entry in sorted(os.listdir(target), key=lambda s: (not os.path.isdir(target / s), s.lower())):
                if entry.startswith("."):
                    continue
                full = target / entry
                rel = str(full.relative_to(work_dir))
                entries.append(
                    FsEntry(
                        name=entry,
                        path=rel,
                        type="directory" if full.is_dir() else "file",
                        size=full.stat().st_size if full.is_file() else None,
                    )
                )
        except OSError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cannot list directory: {e}",
            )
        return FsListResponse(entries=entries)

    # File
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot read file: {e}",
        )
    return FsReadResponse(content=content, path=str(target.relative_to(work_dir)))


@router.post("/{project_id}/fs")
async def write_fs(
    project_id: str,
    req: FsWriteRequest,
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    work_dir = await _resolve_project_dir(project_id, current_user.id)
    target = _resolve_path(work_dir, req.path)

    # Ensure parent directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        target.write_text(req.content, encoding="utf-8")
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot write file: {e}",
        )
    return {"detail": "File saved", "path": str(target.relative_to(work_dir))}
