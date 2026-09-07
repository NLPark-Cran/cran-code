"""Tests for the /api/v2/memories REST endpoints (ADR 002)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

from cran_code.web.api_v2 import memories as memories_api
from cran_code.web.app import create_app
from cran_code.web.db import Base
from cran_code.web.db import memories as memory_store
from cran_code.web.db.models import User


@pytest.fixture
async def session_factory(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Temporary sqlite DB patched into the memory store."""
    engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/mem.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(memory_store, "AsyncSessionLocal", factory)
    yield factory
    await engine.dispose()


@pytest.fixture
async def user(session_factory) -> User:
    async with session_factory() as session:
        user = User(email="alice@x.test", username="alice", password_hash="x")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def test_list_memories_active_newest_first(session_factory, user: User) -> None:
    first = await memory_store.remember(user_id=user.id, kind="fact", content="fact one")
    second = await memory_store.remember(user_id=user.id, kind="fact", content="fact two")
    await memory_store.remember(user_id="other-user", kind="fact", content="not yours")
    await memory_store.archive(user.id, first.memory.id)

    resp = await memories_api.list_memories(
        q=None, include_archived=False, limit=50, offset=0, current_user=user
    )
    assert [m.id for m in resp] == [second.memory.id]
    assert resp[0].kind == "fact"
    assert resp[0].archived is False
    assert resp[0].created_at and resp[0].updated_at

    with_archived = await memories_api.list_memories(
        q=None, include_archived=True, limit=50, offset=0, current_user=user
    )
    assert [m.id for m in with_archived] == [second.memory.id, first.memory.id]


async def test_list_memories_search_and_pagination(session_factory, user: User) -> None:
    for i in range(4):
        await memory_store.remember(user_id=user.id, kind="fact", content=f"entry {i}")
    await memory_store.remember(user_id=user.id, kind="preference", content="unrelated")

    hits = await memories_api.list_memories(
        q="entry", include_archived=False, limit=50, offset=0, current_user=user
    )
    assert len(hits) == 4

    page = await memories_api.list_memories(
        q="entry", include_archived=False, limit=2, offset=2, current_user=user
    )
    assert [m.content for m in page] == ["entry 1", "entry 0"]


async def test_archive_memory_endpoint(session_factory, user: User) -> None:
    saved = await memory_store.remember(user_id=user.id, kind="fact", content="temporary")
    other = await memory_store.remember(user_id="other-user", kind="fact", content="others")

    resp = await memories_api.archive_memory(saved.memory.id, current_user=user)
    assert resp["detail"] == "Memory archived"
    assert (await memory_store.list_for_user(user.id)) == []

    # Not found / not owned -> 404
    with pytest.raises(HTTPException) as exc_info:
        await memories_api.archive_memory(saved.memory.id, current_user=user)
    assert exc_info.value.status_code == 404
    with pytest.raises(HTTPException) as exc_info:
        await memories_api.archive_memory(other.memory.id, current_user=user)
    assert exc_info.value.status_code == 404


def test_memories_endpoints_require_auth() -> None:
    """No token -> 401 before any DB access (v2 JWT layer, require_user)."""
    with TestClient(create_app(session_token="test-token")) as client:
        assert client.get("/api/v2/memories").status_code == 401
        assert client.delete("/api/v2/memories/whatever").status_code == 401
