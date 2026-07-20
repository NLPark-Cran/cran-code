"""Git integration API for projects."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from cran_code.web.auth_v2.jwt import User as JWTUser, require_user
from cran_code.web.db import AsyncSessionLocal, Project, TeamMember

router = APIRouter(prefix="/api/v2/projects", tags=["git"])

_PROJECT_ROOT = Path(
    os.environ.get("CRAN_PROJECT_ROOT", str(Path.home()))
).expanduser().resolve()


class GitStatusResponse(BaseModel):
    branch: str
    ahead: int
    behind: int
    modified: list[str]
    staged: list[str]
    untracked: list[str]
    clean: bool


class GitBranchResponse(BaseModel):
    name: str
    current: bool


class GitCommitResponse(BaseModel):
    hash: str
    short_hash: str
    message: str
    author: str
    date: str


class GitDiffResponse(BaseModel):
    path: str
    diff: str


class GitCommitRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


async def _require_project_dir(project_id: str, user_id: str) -> Path:
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Project has no working directory")

        cwd = Path(project.work_dir).expanduser().resolve()
        try:
            cwd.relative_to(_PROJECT_ROOT)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Project directory outside allowed root",
            )
        if not cwd.exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Working directory does not exist")
        return cwd


async def _run_git(cwd: Path, *args: str) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode or 0, stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace")


@router.get("/{project_id}/git/status", response_model=GitStatusResponse)
async def git_status(
    project_id: str,
    current_user: JWTUser = Depends(require_user),
) -> GitStatusResponse:
    cwd = await _require_project_dir(project_id, current_user.id)
    rc, out, err = await _run_git(cwd, "status", "--porcelain", "-b", "--ahead-behind")
    if rc != 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err or "git status failed")

    branch = "main"
    ahead = 0
    behind = 0
    modified: list[str] = []
    staged: list[str] = []
    untracked: list[str] = []

    for line in out.splitlines():
        if line.startswith("## "):
            branch_part = line[3:].split("...")[0]
            branch = branch_part.strip()
            if "[ahead " in line:
                try:
                    ahead_str = line.split("[ahead ")[1].split("]")[0].split(",")[0]
                    ahead = int(ahead_str)
                except (IndexError, ValueError):
                    pass
            if "[behind " in line:
                try:
                    behind_str = line.split("[behind ")[1].split("]")[0].split(",")[0]
                    behind = int(behind_str)
                except (IndexError, ValueError):
                    pass
            continue
        if len(line) < 3:
            continue
        status_code = line[:2]
        path_str = line[3:].strip()
        if status_code == "??":
            untracked.append(path_str)
        elif status_code[0] != " ":
            staged.append(path_str)
        elif status_code[1] != " ":
            modified.append(path_str)

    return GitStatusResponse(
        branch=branch,
        ahead=ahead,
        behind=behind,
        modified=modified,
        staged=staged,
        untracked=untracked,
        clean=not (modified or staged or untracked),
    )


@router.get("/{project_id}/git/branches", response_model=list[GitBranchResponse])
async def git_branches(
    project_id: str,
    current_user: JWTUser = Depends(require_user),
) -> list[GitBranchResponse]:
    cwd = await _require_project_dir(project_id, current_user.id)
    rc, out, err = await _run_git(cwd, "branch", "-a")
    if rc != 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err or "git branch failed")

    branches: list[GitBranchResponse] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        current = line.startswith("* ")
        name = line[2:].strip() if current else line
        branches.append(GitBranchResponse(name=name, current=current))
    return branches


@router.get("/{project_id}/git/log", response_model=list[GitCommitResponse])
async def git_log(
    project_id: str,
    limit: int = 20,
    current_user: JWTUser = Depends(require_user),
) -> list[GitCommitResponse]:
    cwd = await _require_project_dir(project_id, current_user.id)
    # Clamp the limit to a sane range to avoid unbounded log output.
    limit = min(max(limit, 1), 1000)
    rc, out, err = await _run_git(
        cwd, "log", f"--max-count={limit}", "--pretty=format:%H|%h|%s|%an|%ai"
    )
    if rc != 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err or "git log failed")

    commits: list[GitCommitResponse] = []
    for line in out.splitlines():
        parts = line.split("|", 4)
        if len(parts) >= 5:
            commits.append(
                GitCommitResponse(
                    hash=parts[0],
                    short_hash=parts[1],
                    message=parts[2],
                    author=parts[3],
                    date=parts[4],
                )
            )
    return commits


@router.get("/{project_id}/git/diff", response_model=list[GitDiffResponse])
async def git_diff(
    project_id: str,
    staged: bool = False,
    path: str | None = None,
    current_user: JWTUser = Depends(require_user),
) -> list[GitDiffResponse]:
    cwd = await _require_project_dir(project_id, current_user.id)
    args = ["diff", "--no-color"]
    if staged:
        args.append("--staged")
    if path:
        args.append("--")
        args.append(path)

    rc, out, err = await _run_git(cwd, *args)
    if rc != 0 and rc != 1:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err or "git diff failed")

    diffs: list[GitDiffResponse] = []
    if out.strip():
        diffs.append(GitDiffResponse(path=path or "", diff=out))
    return diffs


@router.post("/{project_id}/git/commit")
async def git_commit(
    project_id: str,
    req: GitCommitRequest,
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    cwd = await _require_project_dir(project_id, current_user.id)
    rc, out, err = await _run_git(cwd, "commit", "-m", req.message)
    if rc != 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err or "git commit failed")
    return {"detail": "Committed", "output": out}
