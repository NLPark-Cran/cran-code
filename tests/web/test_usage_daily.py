"""Tests for per-day usage aggregation and admin usage endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from cran_code.web.api_v2 import admin as admin_api
from cran_code.web.api_v2 import users as users_api
from cran_code.web.auth_v2 import jwt as jwt_mod
from cran_code.web.db import Base
from cran_code.web.db.models import UsageRecord, User, UserRole

SessionFactory = async_sessionmaker

UTC = timezone.utc


@pytest.fixture
async def session_factory(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Temporary sqlite DB patched into users/admin modules."""
    engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(users_api, "AsyncSessionLocal", factory)
    monkeypatch.setattr(admin_api, "AsyncSessionLocal", factory)
    yield factory
    await engine.dispose()


async def make_user(
    factory: SessionFactory, username: str, role: UserRole = UserRole.user
) -> User:
    async with factory() as session:
        user = User(
            email=f"{username}@x.test",
            username=username,
            password_hash="x",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def add_usage(
    factory: SessionFactory,
    user_id: str,
    provider_key: str,
    source: str,
    input_tokens: int,
    output_tokens: int,
    model: str = "kimi-for-coding",
    created_at: datetime | None = None,
) -> None:
    async with factory() as session:
        session.add(
            UsageRecord(
                user_id=user_id,
                provider_key=provider_key,
                model=model,
                source=source,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                created_at=created_at or datetime.now(UTC),
            )
        )
        await session.commit()


def days_ago(n: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=n)


class TestMyUsageDaily:
    async def test_groups_same_bucket_and_orders_by_date(
        self, session_factory: SessionFactory
    ):
        user = await make_user(session_factory, "alice")
        today = days_ago(0)
        yesterday = days_ago(1)
        # Same (date, provider, model, source) bucket -> summed
        await add_usage(session_factory, user.id, "kimi", "shared", 10, 5, created_at=today)
        await add_usage(session_factory, user.id, "kimi", "shared", 4, 1, created_at=today)
        # Different source -> separate row
        await add_usage(session_factory, user.id, "kimi", "personal", 7, 3, created_at=today)
        # Different model -> separate row
        await add_usage(
            session_factory, user.id, "kimi", "shared", 1, 1,
            model="kimi-k2", created_at=today,
        )
        # Different day -> separate row
        await add_usage(session_factory, user.id, "kimi", "shared", 20, 10, created_at=yesterday)

        rows = await users_api.get_my_usage_daily(current_user=user)
        by_key = {(r.date, r.provider_key, r.model, r.source): r for r in rows}
        today_str = today.strftime("%Y-%m-%d")
        yesterday_str = yesterday.strftime("%Y-%m-%d")

        bucket = by_key[(today_str, "kimi", "kimi-for-coding", "shared")]
        assert bucket.input_tokens == 14
        assert bucket.output_tokens == 6

        assert (today_str, "kimi", "kimi-for-coding", "personal") in by_key
        assert (today_str, "kimi", "kimi-k2", "shared") in by_key
        older = by_key[(yesterday_str, "kimi", "kimi-for-coding", "shared")]
        assert older.input_tokens == 20

        # Ordered chronologically
        dates = [r.date for r in rows]
        assert dates == sorted(dates)

    async def test_excludes_other_users_and_old_records(
        self, session_factory: SessionFactory
    ):
        alice = await make_user(session_factory, "alice")
        bob = await make_user(session_factory, "bob")
        await add_usage(session_factory, alice.id, "kimi", "shared", 10, 5)
        await add_usage(session_factory, bob.id, "kimi", "shared", 99, 99)
        # Older than the default 30-day window
        await add_usage(
            session_factory, alice.id, "kimi", "shared", 50, 50,
            created_at=days_ago(40),
        )

        rows = await users_api.get_my_usage_daily(current_user=alice)
        assert len(rows) == 1
        assert rows[0].input_tokens == 10

        # A wider window picks the old record up again
        wide = await users_api.get_my_usage_daily(days=90, current_user=alice)
        assert sum(r.input_tokens for r in wide) == 60

    async def test_empty(self, session_factory: SessionFactory):
        user = await make_user(session_factory, "alice")
        assert await users_api.get_my_usage_daily(current_user=user) == []


class TestAdminUsage:
    async def test_aggregates_all_users_with_usernames(
        self, session_factory: SessionFactory
    ):
        admin = await make_user(session_factory, "root", role=UserRole.admin)
        alice = await make_user(session_factory, "alice")
        bob = await make_user(session_factory, "bob")
        await add_usage(session_factory, alice.id, "kimi", "shared", 10, 5)
        await add_usage(session_factory, alice.id, "kimi", "shared", 2, 1)
        await add_usage(session_factory, bob.id, "empty", "personal", 7, 3)

        rows = await admin_api.get_admin_usage(current_user=admin)
        by_user = {r.username: r for r in rows}
        assert set(by_user) == {"alice", "bob"}
        assert by_user["alice"].input_tokens == 12
        assert by_user["alice"].provider_key == "kimi"
        assert by_user["alice"].user_id == alice.id
        assert by_user["bob"].source == "personal"

    async def test_admin_gate_rejects_non_admin(self, session_factory: SessionFactory):
        user = await make_user(session_factory, "alice")
        with pytest.raises(HTTPException) as exc_info:
            await jwt_mod.require_admin(user)
        assert exc_info.value.status_code == 403

        admin = await make_user(session_factory, "root", role=UserRole.admin)
        # require_admin passes admins through
        assert (await jwt_mod.require_admin(admin)).id == admin.id
