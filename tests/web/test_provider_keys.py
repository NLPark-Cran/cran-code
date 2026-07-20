"""Tests for per-user/team provider key storage and related v2 API endpoints."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from pydantic import SecretStr, ValidationError
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from cran_code.config import Config, LLMProvider
from cran_code.web.api_v2 import teams as teams_api
from cran_code.web.api_v2 import users as users_api
from cran_code.web.auth_v2 import jwt as jwt_mod
from cran_code.web.db import Base
from cran_code.web.db import keys as keys_mod
from cran_code.web.db.models import (
    ProviderGrant,
    ProviderPolicy,
    Team,
    TeamMember,
    TeamMemberRole,
    TeamProviderKey,
    UsageRecord,
    User,
    UserProviderKey,
    UserRole,
)

SessionFactory = async_sessionmaker


@pytest.fixture
async def session_factory(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """Temporary sqlite DB patched into users/teams/keys modules."""
    engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(users_api, "AsyncSessionLocal", factory)
    monkeypatch.setattr(teams_api, "AsyncSessionLocal", factory)
    monkeypatch.setattr(keys_mod, "AsyncSessionLocal", factory)
    yield factory
    await engine.dispose()


@pytest.fixture
def fake_config(monkeypatch: pytest.MonkeyPatch) -> Config:
    config = Config()
    config.providers["kimi"] = LLMProvider(
        type="kimi",
        base_url="https://api.kimi.com/coding/v1",
        api_key=SecretStr("sk-global-kimi"),
    )
    config.providers["empty"] = LLMProvider(
        type="openai_legacy",
        base_url="https://x.test/v1",
        api_key=SecretStr(""),
    )
    monkeypatch.setattr(users_api, "load_config", lambda: config)
    monkeypatch.setattr(teams_api, "load_config", lambda: config)
    monkeypatch.setattr(keys_mod, "load_config", lambda: config)
    return config


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


async def make_team(
    factory: SessionFactory, owner: User, slug: str = "t1"
) -> Team:
    async with factory() as session:
        team = Team(name=slug, slug=slug, owner_id=owner.id)
        session.add(team)
        await session.flush()
        session.add(
            TeamMember(team_id=team.id, user_id=owner.id, role=TeamMemberRole.owner)
        )
        await session.commit()
        await session.refresh(team)
        return team


async def add_member(
    factory: SessionFactory,
    team: Team,
    user: User,
    role: TeamMemberRole = TeamMemberRole.member,
) -> None:
    async with factory() as session:
        session.add(TeamMember(team_id=team.id, user_id=user.id, role=role))
        await session.commit()


async def add_usage(
    factory: SessionFactory,
    user_id: str,
    provider_key: str,
    source: str,
    input_tokens: int,
    output_tokens: int,
    model: str = "kimi-for-coding",
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
            )
        )
        await session.commit()


async def set_policy(factory: SessionFactory, provider_key: str, mode: str) -> None:
    async with factory() as session:
        session.add(ProviderPolicy(provider_key=provider_key, shared_mode=mode))
        await session.commit()


async def add_grant(
    factory: SessionFactory,
    provider_key: str,
    subject_type: str,
    subject_id: str,
    quota_tokens: int | None,
    granted_by: str = "admin",
) -> None:
    async with factory() as session:
        session.add(
            ProviderGrant(
                provider_key=provider_key,
                subject_type=subject_type,
                subject_id=subject_id,
                quota_tokens=quota_tokens,
                granted_by=granted_by,
            )
        )
        await session.commit()


class TestTables:
    async def test_new_tables_created(self, session_factory: SessionFactory):
        engine = session_factory.kw["bind"]
        async with engine.begin() as conn:
            names = await conn.run_sync(lambda c: inspect(c).get_table_names())
        for table in (
            "user_provider_keys",
            "team_provider_keys",
            "provider_policies",
            "provider_grants",
            "usage_records",
        ):
            assert table in names


class TestUserProviderKeys:
    async def test_put_get_masking(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        req = users_api.ProviderKeyUpsertRequest(api_key="sk-secret-alice")
        resp = await users_api.upsert_my_provider_key("kimi", req, current_user=user)
        assert resp.provider_key == "kimi"
        assert resp.has_api_key is True

        keys = await users_api.list_my_provider_keys(current_user=user)
        assert len(keys) == 1
        assert keys[0].provider_key == "kimi"
        assert keys[0].has_api_key is True
        assert keys[0].created_at is not None
        assert keys[0].updated_at is not None
        # No key material anywhere
        assert "sk-secret-alice" not in [k.model_dump_json() for k in keys][0]

    async def test_upsert_overwrites(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        await users_api.upsert_my_provider_key(
            "kimi", users_api.ProviderKeyUpsertRequest(api_key="sk-old"), current_user=user
        )
        await users_api.upsert_my_provider_key(
            "kimi", users_api.ProviderKeyUpsertRequest(api_key="sk-new"), current_user=user
        )
        keys = await users_api.list_my_provider_keys(current_user=user)
        assert len(keys) == 1
        resolved = await keys_mod.resolve_provider_key(user.id, "kimi", [])
        assert resolved == ("sk-new", "personal")

    async def test_put_unknown_provider_404(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        with pytest.raises(HTTPException) as exc_info:
            await users_api.upsert_my_provider_key(
                "nope",
                users_api.ProviderKeyUpsertRequest(api_key="sk-x"),
                current_user=user,
            )
        assert exc_info.value.status_code == 404

    async def test_put_empty_key_rejected(self):
        with pytest.raises(ValidationError):
            users_api.ProviderKeyUpsertRequest(api_key="")

    async def test_delete(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        await users_api.upsert_my_provider_key(
            "kimi", users_api.ProviderKeyUpsertRequest(api_key="sk-x"), current_user=user
        )
        resp = await users_api.delete_my_provider_key("kimi", current_user=user)
        assert "detail" in resp
        assert await users_api.list_my_provider_keys(current_user=user) == []
        with pytest.raises(HTTPException) as exc_info:
            await users_api.delete_my_provider_key("kimi", current_user=user)
        assert exc_info.value.status_code == 404


class TestRolePatch:
    async def test_admin_promotes_user(self, session_factory: SessionFactory):
        admin = await make_user(session_factory, "admin", role=UserRole.admin)
        user = await make_user(session_factory, "bob")
        resp = await users_api.update_user_role(
            user.id, users_api.UserRoleUpdate(role="admin"), current_user=admin
        )
        assert resp.role == "admin"

    async def test_invalid_role_400(self, session_factory: SessionFactory):
        admin = await make_user(session_factory, "admin", role=UserRole.admin)
        user = await make_user(session_factory, "bob")
        with pytest.raises(HTTPException) as exc_info:
            await users_api.update_user_role(
                user.id, users_api.UserRoleUpdate(role="superuser"), current_user=admin
            )
        assert exc_info.value.status_code == 400

    async def test_unknown_user_404(self, session_factory: SessionFactory):
        admin = await make_user(session_factory, "admin", role=UserRole.admin)
        with pytest.raises(HTTPException) as exc_info:
            await users_api.update_user_role(
                "no-such-id", users_api.UserRoleUpdate(role="user"), current_user=admin
            )
        assert exc_info.value.status_code == 404

    async def test_self_demotion_blocked(self, session_factory: SessionFactory):
        admin = await make_user(session_factory, "admin", role=UserRole.admin)
        with pytest.raises(HTTPException) as exc_info:
            await users_api.update_user_role(
                admin.id, users_api.UserRoleUpdate(role="user"), current_user=admin
            )
        assert exc_info.value.status_code == 400

    async def test_non_admin_forbidden(self, session_factory: SessionFactory):
        user = await make_user(session_factory, "bob")
        with pytest.raises(HTTPException) as exc_info:
            await jwt_mod.require_admin(user)
        assert exc_info.value.status_code == 403


class TestTeamProviderKeys:
    async def test_owner_crud_masked(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        owner = await make_user(session_factory, "owner")
        team = await make_team(session_factory, owner)
        req = teams_api.TeamProviderKeyUpsertRequest(api_key="sk-team-secret")
        resp = await teams_api.upsert_team_provider_key(
            team.id, "kimi", req, current_user=owner
        )
        assert resp.has_api_key is True

        keys = await teams_api.list_team_provider_keys(team.id, current_user=owner)
        assert [(k.provider_key, k.has_api_key) for k in keys] == [("kimi", True)]
        assert "sk-team-secret" not in keys[0].model_dump_json()

        resp2 = await teams_api.delete_team_provider_key(
            team.id, "kimi", current_user=owner
        )
        assert "detail" in resp2
        with pytest.raises(HTTPException) as exc_info:
            await teams_api.delete_team_provider_key(team.id, "kimi", current_user=owner)
        assert exc_info.value.status_code == 404

    async def test_member_forbidden(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        owner = await make_user(session_factory, "owner")
        member = await make_user(session_factory, "member")
        team = await make_team(session_factory, owner)
        await add_member(session_factory, team, member, TeamMemberRole.member)

        req = teams_api.TeamProviderKeyUpsertRequest(api_key="sk-x")
        with pytest.raises(HTTPException) as exc_info:
            await teams_api.upsert_team_provider_key(
                team.id, "kimi", req, current_user=member
            )
        assert exc_info.value.status_code == 403
        with pytest.raises(HTTPException) as exc_info:
            await teams_api.list_team_provider_keys(team.id, current_user=member)
        assert exc_info.value.status_code == 403

    async def test_team_admin_allowed(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        owner = await make_user(session_factory, "owner")
        admin = await make_user(session_factory, "tadmin")
        team = await make_team(session_factory, owner)
        await add_member(session_factory, team, admin, TeamMemberRole.admin)
        resp = await teams_api.upsert_team_provider_key(
            team.id,
            "kimi",
            teams_api.TeamProviderKeyUpsertRequest(api_key="sk-x"),
            current_user=admin,
        )
        assert resp.has_api_key is True

    async def test_unknown_provider_404(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        owner = await make_user(session_factory, "owner")
        team = await make_team(session_factory, owner)
        with pytest.raises(HTTPException) as exc_info:
            await teams_api.upsert_team_provider_key(
                team.id,
                "nope",
                teams_api.TeamProviderKeyUpsertRequest(api_key="sk-x"),
                current_user=owner,
            )
        assert exc_info.value.status_code == 404

    async def test_unknown_team_404(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        owner = await make_user(session_factory, "owner")
        with pytest.raises(HTTPException) as exc_info:
            await teams_api.list_team_provider_keys("no-such-team", current_user=owner)
        assert exc_info.value.status_code == 404


class TestResolveProviderKey:
    async def test_personal_wins(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        team = await make_team(session_factory, user)
        async with session_factory() as session:
            session.add(
                UserProviderKey(user_id=user.id, provider_key="kimi", api_key="sk-me")
            )
            session.add(
                TeamProviderKey(team_id=team.id, provider_key="kimi", api_key="sk-team")
            )
            await session.commit()
        resolved = await keys_mod.resolve_provider_key(user.id, "kimi", [team.id])
        assert resolved == ("sk-me", "personal")

    async def test_team_fallback(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        team = await make_team(session_factory, user)
        async with session_factory() as session:
            session.add(
                TeamProviderKey(team_id=team.id, provider_key="kimi", api_key="sk-team")
            )
            await session.commit()
        resolved = await keys_mod.resolve_provider_key(user.id, "kimi", [team.id])
        assert resolved == ("sk-team", "team")

    async def test_shared_mode_all(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        # No policy row -> default "all"
        resolved = await keys_mod.resolve_provider_key(user.id, "kimi", [])
        assert resolved == ("sk-global-kimi", "shared")

    async def test_shared_restricted_no_grant(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        await set_policy(session_factory, "kimi", "restricted")
        assert await keys_mod.resolve_provider_key(user.id, "kimi", []) is None

    async def test_shared_restricted_user_grant(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        await set_policy(session_factory, "kimi", "restricted")
        await add_grant(session_factory, "kimi", "user", user.id, 1000)
        resolved = await keys_mod.resolve_provider_key(user.id, "kimi", [])
        assert resolved == ("sk-global-kimi", "shared")

    async def test_shared_restricted_team_grant(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        team = await make_team(session_factory, user)
        await set_policy(session_factory, "kimi", "restricted")
        await add_grant(session_factory, "kimi", "team", team.id, None)
        resolved = await keys_mod.resolve_provider_key(user.id, "kimi", [team.id])
        assert resolved == ("sk-global-kimi", "shared")

    async def test_shared_restricted_admin_bypass(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        admin = await make_user(session_factory, "admin", role=UserRole.admin)
        await set_policy(session_factory, "kimi", "restricted")
        resolved = await keys_mod.resolve_provider_key(admin.id, "kimi", [])
        assert resolved == ("sk-global-kimi", "shared")

    async def test_provider_without_global_key(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        assert await keys_mod.resolve_provider_key(user.id, "empty", []) is None
        assert await keys_mod.resolve_provider_key(user.id, "nope", []) is None

    async def test_get_key_status(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        assert await keys_mod.get_key_status(user, "kimi", []) == "shared"
        async with session_factory() as session:
            session.add(
                UserProviderKey(user_id=user.id, provider_key="kimi", api_key="sk-me")
            )
            await session.commit()
        assert await keys_mod.get_key_status(user, "kimi", []) == "personal"
        assert await keys_mod.get_key_status(user, "nope", []) == "none"


class TestRemainingQuota:
    async def test_not_restricted_unlimited(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        assert await keys_mod.remaining_quota(user.id, "kimi", []) is None

    async def test_quota_math(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        await set_policy(session_factory, "kimi", "restricted")
        await add_grant(session_factory, "kimi", "user", user.id, 100)
        await add_usage(session_factory, user.id, "kimi", "shared", 20, 10)
        # Personal-source usage does not count against the shared quota
        await add_usage(session_factory, user.id, "kimi", "personal", 1000, 1000)
        quota, remaining = await keys_mod.quota_summary(user.id, "kimi", [])
        assert quota == 100
        assert remaining == 70
        assert await keys_mod.remaining_quota(user.id, "kimi", []) == 70

    async def test_unlimited_grant(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        await set_policy(session_factory, "kimi", "restricted")
        await add_grant(session_factory, "kimi", "user", user.id, None)
        assert await keys_mod.remaining_quota(user.id, "kimi", []) is None

    async def test_no_grant(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        await set_policy(session_factory, "kimi", "restricted")
        assert await keys_mod.remaining_quota(user.id, "kimi", []) is None

    async def test_admin_unlimited(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        admin = await make_user(session_factory, "admin", role=UserRole.admin)
        await set_policy(session_factory, "kimi", "restricted")
        assert await keys_mod.remaining_quota(admin.id, "kimi", []) is None

    async def test_team_grant_counts_member_usage(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        owner = await make_user(session_factory, "owner")
        other = await make_user(session_factory, "other")
        team = await make_team(session_factory, owner)
        await add_member(session_factory, team, other)
        await set_policy(session_factory, "kimi", "restricted")
        await add_grant(session_factory, "kimi", "team", team.id, 100)
        await add_usage(session_factory, other.id, "kimi", "shared", 30, 10)
        # Owner's remaining reflects the whole team's shared usage
        assert await keys_mod.remaining_quota(owner.id, "kimi", [team.id]) == 60

    async def test_most_restrictive_grant_wins(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        team = await make_team(session_factory, user)
        await set_policy(session_factory, "kimi", "restricted")
        await add_grant(session_factory, "kimi", "user", user.id, 100)
        await add_grant(session_factory, "kimi", "team", team.id, 50)
        await add_usage(session_factory, user.id, "kimi", "shared", 20, 0)
        # user grant: 100 - 20 = 80; team grant: 50 - 20 = 30 -> min
        assert await keys_mod.remaining_quota(user.id, "kimi", [team.id]) == 30


class TestUsageEndpoint:
    async def test_aggregation_and_quota(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        await set_policy(session_factory, "kimi", "restricted")
        await add_grant(session_factory, "kimi", "user", user.id, 100)
        await add_usage(session_factory, user.id, "kimi", "personal", 10, 5)
        await add_usage(session_factory, user.id, "kimi", "shared", 20, 10)
        await add_usage(session_factory, user.id, "kimi", "shared", 4, 1)
        await add_usage(session_factory, user.id, "empty", "team", 3, 2)

        rows = await users_api.get_my_usage(current_user=user)
        by_key = {(r.provider_key, r.source): r for r in rows}
        assert set(by_key) == {
            ("kimi", "personal"),
            ("kimi", "shared"),
            ("empty", "team"),
        }

        personal = by_key[("kimi", "personal")]
        assert personal.input_tokens == 10
        assert personal.output_tokens == 5
        assert personal.total_tokens == 15
        assert personal.quota_tokens is None
        assert personal.remaining_tokens is None

        shared = by_key[("kimi", "shared")]
        assert shared.input_tokens == 24
        assert shared.output_tokens == 11
        assert shared.total_tokens == 35
        assert shared.quota_tokens == 100
        assert shared.remaining_tokens == 65

        team = by_key[("empty", "team")]
        assert team.total_tokens == 5
        assert team.quota_tokens is None

    async def test_empty_usage(
        self, session_factory: SessionFactory, fake_config: Config
    ):
        user = await make_user(session_factory, "alice")
        assert await users_api.get_my_usage(current_user=user) == []
