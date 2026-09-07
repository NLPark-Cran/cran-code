"""Cross-session memory API (companion mode, ADR 002).

Users can list and archive their own memories. Writes happen via the
RememberMemory tool inside sessions; the REST surface is deliberately
read/archive-only for v1 (a management UI comes later).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from cran_code.web.auth_v2.jwt import User as JWTUser
from cran_code.web.auth_v2.jwt import require_user
from cran_code.web.db import memories as memory_store
from cran_code.web.db.models import Memory

router = APIRouter(prefix="/api/v2/memories", tags=["memories"])


class MemoryResponse(BaseModel):
    id: str
    kind: str
    content: str
    salience: float
    evidence: str | None
    project_id: str | None
    source_session_id: str | None
    archived: bool
    created_at: str
    updated_at: str


def _memory_response(m: Memory) -> MemoryResponse:
    return MemoryResponse(
        id=m.id,
        kind=m.kind,
        content=m.content,
        salience=m.salience,
        evidence=m.evidence,
        project_id=m.project_id,
        source_session_id=m.source_session_id,
        archived=m.archived,
        created_at=m.created_at.isoformat(),
        updated_at=m.updated_at.isoformat(),
    )


@router.get("", response_model=list[MemoryResponse])
async def list_memories(
    current_user: Annotated[JWTUser, Depends(require_user)],
    q: str | None = Query(default=None, max_length=200),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[MemoryResponse]:
    """List the current user's memories, newest first (active only by default)."""
    memories = await memory_store.list_for_user(
        current_user.id,
        query=q,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    return [_memory_response(m) for m in memories]


@router.delete("/{memory_id}")
async def archive_memory(
    memory_id: str,
    current_user: Annotated[JWTUser, Depends(require_user)],
) -> dict[str, str]:
    """Archive one of the current user's memories (never hard-deleted)."""
    memory = await memory_store.archive(current_user.id, memory_id)
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )
    return {"detail": "Memory archived"}
