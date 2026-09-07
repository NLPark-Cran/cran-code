"""Tests for session device binding + worker MCP relay injection (ADR 004)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import UUID

import pytest
from kaos.path import KaosPath
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

import cran_code.web.db as db_mod
from cran_code.session import Session
from cran_code.session_state import load_session_state, save_session_state
from cran_code.web import tunnel as tunnel_mod
from cran_code.web.app import create_app
from cran_code.web.auth_v2 import jwt as jwt_mod
from cran_code.web.auth_v2.jwt import create_access_token
from cran_code.web.db import Base
from cran_code.web.db import devices as device_store
from cran_code.web.db.models import User
from cran_code.web.runner import worker as worker_mod
from cran_code.web.runner.device_relay import ENV_DEVICE_MCP_CONFIG, device_mcp_env


@pytest.fixture
def isolated_share_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    share_dir = tmp_path / "share"
    share_dir.mkdir()

    def _get_share_dir() -> Path:
        share_dir.mkdir(parents=True, exist_ok=True)
        return share_dir

    monkeypatch.setattr("cran_code.share.get_share_dir", _get_share_dir)
    monkeypatch.setattr("cran_code.metadata.get_share_dir", _get_share_dir)
    return share_dir


@pytest.fixture
async def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Temporary sqlite DB patched into the device store and both JWT paths."""
    engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/dev.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(device_store, "AsyncSessionLocal", factory)
    monkeypatch.setattr(jwt_mod, "AsyncSessionLocal", factory)
    monkeypatch.setattr(db_mod, "AsyncSessionLocal", factory)
    yield factory
    await engine.dispose()


@pytest.fixture
async def user(session_factory) -> User:
    async with session_factory() as session:
        user = User(email="carol@x.test", username="carol", password_hash="x")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# --- worker.py config merge ---------------------------------------------------


def test_worker_merges_device_mcp_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    global_cfg = tmp_path / "mcp.json"
    global_cfg.write_text(json.dumps({"mcpServers": {"local": {"url": "http://x"}}}))
    monkeypatch.setattr(worker_mod, "get_global_mcp_config_file", lambda: global_cfg)
    fragment = {"mcpServers": {"luoshu-device": {"url": "http://127.0.0.1:1/api/v2/devices/d/mcp"}}}
    monkeypatch.setenv(ENV_DEVICE_MCP_CONFIG, json.dumps(fragment))

    configs = worker_mod.load_mcp_configs()
    assert len(configs) == 2
    assert configs[0]["mcpServers"]["local"]["url"] == "http://x"
    assert "luoshu-device" in configs[1]["mcpServers"]


def test_worker_skips_invalid_device_mcp_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        worker_mod, "get_global_mcp_config_file", lambda: tmp_path / "missing.json"
    )
    monkeypatch.setenv(ENV_DEVICE_MCP_CONFIG, "{not json")
    assert worker_mod.load_mcp_configs() == []


# --- device_mcp_env -------------------------------------------------------------


async def _new_session(tmp_path: Path) -> Session:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    return await Session.create(KaosPath.unsafe_from_local_path(work))


async def test_device_mcp_env_mints_relay_token(
    isolated_share_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = await _new_session(tmp_path)
    state = load_session_state(session.dir)
    state.owner_id = "user-1"
    state.device_id = "dev-1"
    save_session_state(state, session.dir)
    from cran_code.web.store.sessions import invalidate_sessions_cache

    invalidate_sessions_cache()
    monkeypatch.setenv("CRAN_WEB_PORT", "5496")

    env = await device_mcp_env(UUID(session.id))
    config = json.loads(env[ENV_DEVICE_MCP_CONFIG])
    server = config["mcpServers"]["luoshu-device"]
    assert server["url"] == "http://127.0.0.1:5496/api/v2/devices/dev-1/mcp"
    token = server["headers"]["Authorization"].removeprefix("Bearer ")
    grant = tunnel_mod.registry.resolve_relay_token(token)
    assert grant is not None
    assert grant.session_id == session.id
    assert grant.device_id == "dev-1"
    assert grant.owner_id == "user-1"
    tunnel_mod.registry.revoke_session(session.id)


async def test_device_mcp_env_noop_without_binding(
    isolated_share_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = await _new_session(tmp_path)
    from cran_code.web.store.sessions import invalidate_sessions_cache

    invalidate_sessions_cache()
    monkeypatch.setenv("CRAN_WEB_PORT", "5496")
    assert await device_mcp_env(UUID(session.id)) == {}

    # No web port -> no relay URL can be built.
    monkeypatch.delenv("CRAN_WEB_PORT")
    state = load_session_state(session.dir)
    state.device_id = "dev-1"
    save_session_state(state, session.dir)
    invalidate_sessions_cache()
    assert await device_mcp_env(UUID(session.id)) == {}


# --- create_session device binding -------------------------------------------


def test_create_session_binds_device(
    isolated_share_dir: Path, session_factory, user: User, tmp_path: Path
) -> None:
    device, _ = asyncio.run(device_store.create_device(user.id, "rig"))
    with TestClient(create_app(session_token="test-token")) as client:
        resp = client.post(
            "/api/sessions/",
            json={"work_dir": str(tmp_path / "w1"), "create_dir": True, "device_id": device.id},
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["device_id"] == device.id
        session_dir = Path(resp.json()["session_dir"])
        assert load_session_state(session_dir).device_id == device.id


def test_create_session_device_binding_rejected(
    isolated_share_dir: Path, session_factory, user: User, tmp_path: Path
) -> None:
    device, _ = asyncio.run(device_store.create_device(user.id, "rig"))
    with TestClient(create_app(session_token="test-token")) as client:
        # Anonymous (v1 session token) callers cannot bind devices.
        resp = client.post(
            "/api/sessions/",
            json={"work_dir": str(tmp_path / "w2"), "create_dir": True, "device_id": device.id},
        )
        assert resp.status_code == 401

        # A signed-in user cannot bind someone else's (or a missing) device.
        resp = client.post(
            "/api/sessions/",
            json={"work_dir": str(tmp_path / "w3"), "create_dir": True, "device_id": "nope"},
            headers={"Authorization": f"Bearer {create_access_token(user.id)}"},
        )
        assert resp.status_code == 404
