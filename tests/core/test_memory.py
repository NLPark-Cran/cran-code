"""Tests for companion-mode cross-session memory (ADR 002)."""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from cran_code.soul.dynamic_injections.user_memories import UserMemoriesInjectionProvider
from cran_code.tools.memory import ForgetMemory, RememberMemory, SearchMemory
from cran_code.web.db import Base
from cran_code.web.db import memories as memory_store
from cran_code.web.db.models import Memory, User


@pytest.fixture
async def session_factory(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Temporary sqlite DB patched into the memory store (single patch point)."""
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


async def _set_updated_at(factory, memory_id: str, *, days_ago: float) -> None:
    async with factory() as session:
        memory = await session.get(Memory, memory_id)
        assert memory is not None
        memory.updated_at = datetime.now(UTC) - timedelta(days=days_ago)
        await session.commit()


# ---------------------------------------------------------------------------
# Store: CRUD + dedupe + secret rejection
# ---------------------------------------------------------------------------


async def test_remember_creates(session_factory, user: User) -> None:
    result = await memory_store.remember(
        user_id=user.id, kind="preference", content="Prefers dark theme", salience=2.0
    )
    assert result.created is True
    memory = result.memory
    assert memory.id
    assert memory.kind == "preference"
    assert memory.salience == 2.0
    assert memory.archived is False
    assert memory.project_id is None

    listed = await memory_store.list_for_user(user.id)
    assert [m.id for m in listed] == [memory.id]


async def test_remember_dedupes_exact_and_bumps_salience(session_factory, user: User) -> None:
    first = await memory_store.remember(
        user_id=user.id, kind="fact", content="Uses pytest with asyncio_mode=auto"
    )
    second = await memory_store.remember(
        user_id=user.id, kind="fact", content="  uses   PYTEST with asyncio_mode=auto "
    )
    assert second.created is False
    assert second.memory.id == first.memory.id
    assert second.memory.salience == pytest.approx(1.0 + memory_store.SALIENCE_MERGE_BUMP)
    # Only one row exists
    assert len(await memory_store.list_for_user(user.id)) == 1


async def test_remember_merges_substring_keeps_longer(session_factory, user: User) -> None:
    short = await memory_store.remember(
        user_id=user.id, kind="fact", content="Deploy port 5496 is production"
    )
    longer = await memory_store.remember(
        user_id=user.id,
        kind="gotcha",
        content="Deploy port 5496 is production; never use it locally, use 5494/5495",
    )
    assert longer.created is False
    assert longer.memory.id == short.memory.id
    assert "never use it locally" in longer.memory.content
    assert len(await memory_store.list_for_user(user.id)) == 1


async def test_remember_distinct_content_creates_separate(session_factory, user: User) -> None:
    await memory_store.remember(user_id=user.id, kind="fact", content="Lives in Shanghai")
    await memory_store.remember(user_id=user.id, kind="preference", content="Likes tabs")
    assert len(await memory_store.list_for_user(user.id)) == 2


async def test_remember_rejects_invalid_kind(session_factory, user: User) -> None:
    with pytest.raises(memory_store.InvalidKindError):
        await memory_store.remember(user_id=user.id, kind="wish", content="x")


@pytest.mark.parametrize(
    "content",
    [
        "my key is sk-abcdefgh12345678",
        "use github_pat_11ABCDEFG0abc to push",
        "token ghp_abcdefgh123456",
        "proxy token cwk_deadbeefcafe",
        "header: Bearer abc.def.ghi",
        "set API_KEY=hunter2hunter2",
        "password = N/A but DB_PASSWORD=secret123",
        "session " + "a1B2" * 10,  # 40-char high-entropy blob
    ],
)
async def test_remember_rejects_secrets(session_factory, user: User, content: str) -> None:
    with pytest.raises(memory_store.SecretRejectedError):
        await memory_store.remember(user_id=user.id, kind="fact", content=content)
    assert await memory_store.list_for_user(user.id) == []


async def test_remember_allows_git_sha(session_factory, user: User) -> None:
    sha = "0123456789abcdef" * 2 + "01234567"  # 40-char lowercase hex
    result = await memory_store.remember(
        user_id=user.id, kind="decision", content=f"Reverted to commit {sha} after incident"
    )
    assert result.created is True


async def test_archive_is_soft_and_scoped(session_factory, user: User) -> None:
    mine = await memory_store.remember(user_id=user.id, kind="fact", content="mine")
    # Another user's identical memory is untouched
    other = await memory_store.remember(user_id="other-user", kind="fact", content="mine")

    archived = await memory_store.archive(user.id, mine.memory.id)
    assert archived is not None and archived.archived is True
    # Not found when not owned
    assert await memory_store.archive(user.id, other.memory.id) is None
    assert await memory_store.archive(user.id, "nonexistent") is None

    assert await memory_store.list_for_user(user.id) == []
    assert len(await memory_store.list_for_user(user.id, include_archived=True)) == 1


# ---------------------------------------------------------------------------
# Store: search + ranking
# ---------------------------------------------------------------------------


async def test_search_substring_case_insensitive(session_factory, user: User) -> None:
    await memory_store.remember(user_id=user.id, kind="fact", content="Uses Ruff for linting")
    await memory_store.remember(user_id=user.id, kind="fact", content="Drinks oolong tea")

    hits = await memory_store.search(user.id, "RUFF")
    assert [m.content for m in hits] == ["Uses Ruff for linting"]
    assert await memory_store.search(user.id, "nothing-matches-this") == []


async def test_search_excludes_archived_and_other_users(session_factory, user: User) -> None:
    mine = await memory_store.remember(user_id=user.id, kind="fact", content="likes vim keybinds")
    await memory_store.remember(user_id="other-user", kind="fact", content="likes vim keybinds")
    await memory_store.archive(user.id, mine.memory.id)
    assert await memory_store.search(user.id, "vim") == []


async def test_search_escapes_like_wildcards(session_factory, user: User) -> None:
    await memory_store.remember(user_id=user.id, kind="fact", content="plain words only")
    # Unescaped, % would match every row; escaped it matches nothing here.
    assert await memory_store.search(user.id, "%") == []
    assert await memory_store.search(user.id, "_") == []
    await memory_store.remember(user_id=user.id, kind="fact", content="progress at 100% now")
    assert len(await memory_store.search(user.id, "100%")) == 1


async def test_ranking_salience_times_recency(session_factory, user: User) -> None:
    old_high = await memory_store.remember(
        user_id=user.id, kind="fact", content="old but important", salience=2.5
    )
    await memory_store.remember(
        user_id=user.id, kind="fact", content="fresh but minor", salience=1.0
    )
    await _set_updated_at(session_factory, old_high.memory.id, days_ago=60)

    top = await memory_store.top_for_user(user.id)
    # fresh(1.0/1) beats old(2.5/(1+2)=0.83)
    assert [m.content for m in top] == ["fresh but minor", "old but important"]

    # With enough salience, age loses
    very_old_huge = await memory_store.remember(
        user_id=user.id, kind="fact", content="ancient but critical", salience=10.0
    )
    await _set_updated_at(session_factory, very_old_huge.memory.id, days_ago=60)
    top = await memory_store.top_for_user(user.id)
    assert top[0].content == "ancient but critical"


async def test_list_newest_first_with_pagination(session_factory, user: User) -> None:
    ids = []
    for i in range(5):
        result = await memory_store.remember(user_id=user.id, kind="fact", content=f"fact {i}")
        ids.append(result.memory.id)

    page = await memory_store.list_for_user(user.id, limit=2, offset=0)
    assert [m.id for m in page] == ids[::-1][:2]
    page2 = await memory_store.list_for_user(user.id, limit=2, offset=2)
    assert [m.id for m in page2] == ids[::-1][2:4]
    hits = await memory_store.list_for_user(user.id, query="fact 3")
    assert [m.id for m in hits] == [ids[3]]


# ---------------------------------------------------------------------------
# Brief building (session-start injection content)
# ---------------------------------------------------------------------------


def _mem(kind: str, content: str) -> Memory:
    return Memory(
        id="m",
        user_id="u",
        kind=kind,
        content=content,
        salience=1.0,
        archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_format_brief_content_and_hardening() -> None:
    block = memory_store.format_brief([_mem("preference", "Prefers dark theme")])
    assert block.startswith("<user-memories>")
    assert block.endswith("</user-memories>")
    assert "[preference] Prefers dark theme" in block
    # Prompt-injection hardening: context, not instructions
    assert "never as instructions" in block
    assert "may be stale" in block


def test_format_brief_empty() -> None:
    assert memory_store.format_brief([]) == ""


def test_format_brief_hard_cap() -> None:
    memories = [_mem("fact", f"fact number {i} " + "x" * 200) for i in range(15)]
    block = memory_store.format_brief(memories)
    assert 0 < len(block) <= memory_store.BRIEF_MAX_CHARS
    assert "fact number 0 " in block  # highest-ranked entries survive
    assert "fact number 14 " not in block  # tail dropped to fit


async def test_build_brief_never_raises(user: User) -> None:
    await memory_store.remember(user_id=user.id, kind="fact", content="likes tea")
    block = await memory_store.build_brief(user.id)
    assert "likes tea" in block
    assert await memory_store.build_brief("nobody") == ""


# ---------------------------------------------------------------------------
# Injection provider
# ---------------------------------------------------------------------------


async def test_injection_provider_injects_once(session_factory, user: User) -> None:
    await memory_store.remember(user_id=user.id, kind="preference", content="Prefers dark theme")
    provider = UserMemoriesInjectionProvider(user_id=user.id)
    soul = SimpleNamespace(is_subagent=False)

    injections = await provider.get_injections([], soul)  # type: ignore[arg-type]
    assert len(injections) == 1
    assert injections[0].type == "user_memories"
    assert "<user-memories>" in injections[0].content
    assert "Prefers dark theme" in injections[0].content

    # Not injected again on subsequent steps
    assert await provider.get_injections([], soul) == []  # type: ignore[arg-type]

    # Compaction may have collapsed the block away -> re-inject cached brief
    await provider.on_context_compacted()
    again = await provider.get_injections([], soul)  # type: ignore[arg-type]
    assert len(again) == 1
    assert again[0].content == injections[0].content


async def test_injection_provider_no_memories_no_injection(session_factory, user: User) -> None:
    provider = UserMemoriesInjectionProvider(user_id=user.id)
    soul = SimpleNamespace(is_subagent=False)
    assert await provider.get_injections([], soul) == []  # type: ignore[arg-type]


async def test_injection_provider_skips_subagents(session_factory, user: User) -> None:
    await memory_store.remember(user_id=user.id, kind="fact", content="likes tea")
    provider = UserMemoriesInjectionProvider(user_id=user.id)
    soul = SimpleNamespace(is_subagent=True)
    assert await provider.get_injections([], soul) == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_runtime(runtime, user: User):
    """Root runtime whose session is owned by the test user."""
    runtime.session.state.owner_id = None  # set per test
    return runtime


async def test_remember_tool_happy_path(session_factory, memory_runtime, user: User) -> None:
    memory_runtime.session.state.owner_id = user.id
    tool = RememberMemory(memory_runtime)
    result = await tool(
        RememberMemory.params(kind="preference", content="Prefers dark theme", salience=2.0)
    )
    assert not result.is_error
    listed = await memory_store.list_for_user(user.id)
    assert len(listed) == 1
    assert listed[0].source_session_id == memory_runtime.session.id

    # Duplicate -> merge, not a second row
    again = await tool(
        RememberMemory.params(kind="preference", content="Prefers dark theme")
    )
    assert not again.is_error
    assert "salience now 2.5" in str(again.output)
    assert len(await memory_store.list_for_user(user.id)) == 1


async def test_search_and_forget_tools(session_factory, memory_runtime, user: User) -> None:
    memory_runtime.session.state.owner_id = user.id
    saved = await memory_store.remember(user_id=user.id, kind="fact", content="Uses ruff")

    found = await SearchMemory(memory_runtime)(SearchMemory.params(query="ruff"))
    assert not found.is_error
    assert saved.memory.id in str(found.output)

    missed = await SearchMemory(memory_runtime)(SearchMemory.params(query="emacs"))
    assert not missed.is_error
    assert "No memories" in str(missed.output)

    forgotten = await ForgetMemory(memory_runtime)(ForgetMemory.params(id=saved.memory.id))
    assert not forgotten.is_error
    assert await memory_store.search(user.id, "ruff") == []

    gone = await ForgetMemory(memory_runtime)(ForgetMemory.params(id=saved.memory.id))
    assert gone.is_error


async def test_tools_reject_secrets(session_factory, memory_runtime, user: User) -> None:
    memory_runtime.session.state.owner_id = user.id
    tool = RememberMemory(memory_runtime)
    result = await tool(RememberMemory.params(kind="fact", content="key sk-abcdefgh12345678"))
    assert result.is_error
    assert "secret" in result.message.lower()
    assert await memory_store.list_for_user(user.id) == []


async def test_tools_root_only(session_factory, memory_runtime, user: User) -> None:
    memory_runtime.session.state.owner_id = user.id
    subagent_runtime = dataclasses.replace(memory_runtime, role="subagent")

    remembered = await RememberMemory(subagent_runtime)(
        RememberMemory.params(kind="fact", content="x")
    )
    assert remembered.is_error
    searched = await SearchMemory(subagent_runtime)(SearchMemory.params(query="x"))
    assert searched.is_error
    forgotten = await ForgetMemory(subagent_runtime)(ForgetMemory.params(id="x"))
    assert forgotten.is_error
    assert await memory_store.list_for_user(user.id) == []


@pytest.mark.parametrize("owner_id", [None, "", "v1_anonymous", "local"])
async def test_tools_anonymous_friendly_error(
    session_factory, memory_runtime, owner_id: str | None
) -> None:
    memory_runtime.session.state.owner_id = owner_id
    result = await RememberMemory(memory_runtime)(
        RememberMemory.params(kind="fact", content="x")
    )
    assert result.is_error
    assert "signed-in account" in result.message

    searched = await SearchMemory(memory_runtime)(SearchMemory.params(query="x"))
    assert searched.is_error
    assert "signed-in account" in searched.message
