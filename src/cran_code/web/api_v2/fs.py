"""Filesystem access API for IDE integration."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from cran_code.web.auth_v2.jwt import User as JWTUser, require_user
from cran_code.web.db import AsyncSessionLocal, Activity, Project, TeamMember
from cran_code.web.db.models import ActivityType

router = APIRouter(prefix="/api/v2/projects", tags=["fs"])

_PROJECT_ROOT = Path(
    os.environ.get("CRAN_PROJECT_ROOT", str(Path.home()))
).expanduser().resolve()


_MAX_FILE_SIZE = int(os.environ.get("CRAN_MAX_FILE_SIZE", "10485760"))  # 10 MB

# Sensitive path components that must never be readable/downloadable via the fs API.
_SENSITIVE_COMPONENTS = frozenset({".env", ".git", ".ssh", ".aws"})
_SENSITIVE_CONFIG_DIRS = frozenset({".cran", ".kimi", ".config"})
_SENSITIVE_CONFIG_FILES = frozenset({"server.env", "config.toml"})


def _is_sensitive_path(rel_path: Path) -> bool:
    """Whether a path (relative to the project dir) touches sensitive files."""
    parts = rel_path.parts
    if any(part in _SENSITIVE_COMPONENTS for part in parts):
        return True
    # server.env / config.toml anywhere under a .cran/.kimi/.config directory.
    return bool(parts) and parts[-1] in _SENSITIVE_CONFIG_FILES and any(
        part in _SENSITIVE_CONFIG_DIRS for part in parts[:-1]
    )


def _ensure_not_sensitive(target: Path, work_dir: Path) -> None:
    """Reject reads/downloads of sensitive files (env, git, ssh, credentials)."""
    if _is_sensitive_path(target.relative_to(work_dir)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to sensitive paths is not allowed",
        )


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


async def _record_activity(
    project_id: str,
    user_id: str,
    activity_type: ActivityType,
    payload: str | None,
) -> None:
    """Record a project activity in the background.

    Errors are swallowed so that filesystem operations do not fail because of
    activity logging.
    """
    try:
        async with AsyncSessionLocal() as session:
            activity = Activity(
                project_id=project_id,
                user_id=user_id,
                type=activity_type,
                payload=payload,
            )
            session.add(activity)
            await session.commit()
    except Exception:
        # Activities are best-effort; don't break the actual file operation.
        pass


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
        try:
            work_dir.relative_to(_PROJECT_ROOT)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Project directory outside allowed root",
            )
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
    _ensure_not_sensitive(target, work_dir)

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
        if target.stat().st_size > _MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large to read (max {_MAX_FILE_SIZE} bytes)",
            )
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

    if len(req.content.encode("utf-8")) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {_MAX_FILE_SIZE} bytes)",
        )

    # Ensure parent directory exists
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        target.write_text(req.content, encoding="utf-8")
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot write file: {e}",
        )

    await _record_activity(
        project_id,
        current_user.id,
        ActivityType.file_edited,
        str(target.relative_to(work_dir)),
    )
    return {"detail": "File saved", "path": str(target.relative_to(work_dir))}


@router.post("/{project_id}/fs/upload")
async def upload_fs(
    project_id: str,
    file: UploadFile = File(...),
    path: str = Query("", max_length=2000),
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    """Upload a file into the project working directory.

    The `path` query parameter is the relative directory where the file should
    be stored. The uploaded file's original filename is appended to it.
    """
    work_dir = await _resolve_project_dir(project_id, current_user.id)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file has no filename",
        )

    # Build a safe relative path: path/filename
    rel_dir = path.strip("/")
    rel_path = f"{rel_dir}/{file.filename}" if rel_dir else file.filename
    target = _resolve_path(work_dir, rel_path)

    # Reject overly large uploads
    contents = await file.read()
    if len(contents) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {_MAX_FILE_SIZE} bytes)",
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_bytes(contents)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot write uploaded file: {e}",
        )

    saved_path = str(target.relative_to(work_dir))
    await _record_activity(
        project_id,
        current_user.id,
        ActivityType.file_uploaded,
        saved_path,
    )
    return {"detail": "File uploaded", "path": saved_path}


@router.get("/{project_id}/fs/download")
async def download_fs(
    project_id: str,
    path: str = Query(..., min_length=1, max_length=2000),
    current_user: JWTUser = Depends(require_user),
) -> Response:
    """Download a file from the project working directory."""
    from fastapi.responses import FileResponse

    work_dir = await _resolve_project_dir(project_id, current_user.id)
    target = _resolve_path(work_dir, path)
    _ensure_not_sensitive(target, work_dir)

    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot download a directory",
        )

    await _record_activity(
        project_id,
        current_user.id,
        ActivityType.file_downloaded,
        str(target.relative_to(work_dir)),
    )

    return FileResponse(
        path=target,
        filename=target.name,
        media_type="application/octet-stream",
    )


@router.delete("/{project_id}/fs")
async def delete_fs(
    project_id: str,
    path: str = Query(..., min_length=1, max_length=2000),
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    """Delete a file or directory inside the project working directory."""
    work_dir = await _resolve_project_dir(project_id, current_user.id)
    target = _resolve_path(work_dir, path)

    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Path not found")

    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot delete path: {e}",
        )

    await _record_activity(
        project_id,
        current_user.id,
        ActivityType.file_deleted,
        str(target.relative_to(work_dir)),
    )
    return {"detail": "Deleted", "path": str(target.relative_to(work_dir))}


@router.post("/{project_id}/fs/copy")
async def copy_fs(
    project_id: str,
    src: str = Query(..., min_length=1, max_length=2000),
    dst: str = Query(..., min_length=1, max_length=2000),
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    """Copy a file or directory to another path inside the project."""
    work_dir = await _resolve_project_dir(project_id, current_user.id)
    source = _resolve_path(work_dir, src)
    destination = _resolve_path(work_dir, dst)

    if not source.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    if destination.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Destination already exists",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot copy: {e}",
        )

    await _record_activity(
        project_id,
        current_user.id,
        ActivityType.file_edited,
        f"copied {src} to {dst}",
    )
    return {"detail": "Copied", "src": src, "dst": dst}


@router.post("/{project_id}/fs/move")
async def move_fs(
    project_id: str,
    src: str = Query(..., min_length=1, max_length=2000),
    dst: str = Query(..., min_length=1, max_length=2000),
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    """Move (rename) a file or directory to another path inside the project."""
    work_dir = await _resolve_project_dir(project_id, current_user.id)
    source = _resolve_path(work_dir, src)
    destination = _resolve_path(work_dir, dst)

    if not source.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    if destination.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Destination already exists",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(source), str(destination))
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot move: {e}",
        )

    await _record_activity(
        project_id,
        current_user.id,
        ActivityType.file_edited,
        f"moved {src} to {dst}",
    )
    return {"detail": "Moved", "src": src, "dst": dst}


@router.post("/{project_id}/fs/compress")
async def compress_fs(
    project_id: str,
    path: str = Query(..., min_length=1, max_length=2000),
    archive: str = Query(..., min_length=1, max_length=2000),
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    """Compress a file or directory into a zip archive inside the project."""
    work_dir = await _resolve_project_dir(project_id, current_user.id)
    source = _resolve_path(work_dir, path)
    archive_path = _resolve_path(work_dir, archive)

    if not source.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    # Only support zip archives for simplicity and security
    if not archive_path.name.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip archives are supported",
        )

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if archive_path.exists():
            archive_path.unlink()
        root_dir = source.parent
        base_dir = source.name
        shutil.make_archive(
            str(archive_path.with_suffix("")),
            "zip",
            root_dir=str(root_dir),
            base_dir=base_dir,
        )
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot compress: {e}",
        )

    await _record_activity(
        project_id,
        current_user.id,
        ActivityType.file_edited,
        f"compressed {path} to {archive}",
    )
    return {"detail": "Compressed", "path": archive}


@router.post("/{project_id}/fs/extract")
async def extract_fs(
    project_id: str,
    archive: str = Query(..., min_length=1, max_length=2000),
    dest: str = Query("", max_length=2000),
    current_user: JWTUser = Depends(require_user),
) -> dict[str, str]:
    """Extract a zip archive inside the project working directory."""
    work_dir = await _resolve_project_dir(project_id, current_user.id)
    archive_path = _resolve_path(work_dir, archive)
    destination = _resolve_path(work_dir, dest) if dest else archive_path.parent

    if not archive_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archive not found")
    if not archive_path.name.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip archives are supported",
        )

    destination.mkdir(parents=True, exist_ok=True)
    try:
        shutil.unpack_archive(str(archive_path), str(destination), "zip")
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cannot extract: {e}",
        )

    await _record_activity(
        project_id,
        current_user.id,
        ActivityType.file_edited,
        f"extracted {archive} to {dest or '.'}",
    )
    return {"detail": "Extracted", "path": dest or str(destination.relative_to(work_dir))}
