"""Tests for the Luoshu device registry + reverse tunnel (ADR 004).

Covers: device store, REST endpoints (auth/CRUD/revoke), tunnel WS auth,
and the full relay round trip (worker POST → tunnel → device → response,
including request-id rewriting).
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from cran_code.web import tunnel as tunnel_mod
from cran_code.web.app import create_app
from cran_code.web.auth_v2 import jwt as jwt_mod
from cran_code.web.auth_v2.jwt import create_access_token
from cran_code.web.db import Base
from cran_code.web.db import devices as device_store
from cran_code.web.db.models import User


@pytest.fixture
async def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Temporary sqlite DB patched into the device store and the JWT layer."""
    engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/dev.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(device_store, "AsyncSessionLocal", factory)
    monkeypatch.setattr(jwt_mod, "AsyncSessionLocal", factory)
    yield factory
    await engine.dispose()


@pytest.fixture
async def user(session_factory) -> User:
    async with session_factory() as session:
        user = User(email="bob@x.test", username="bob", password_hash="x")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


# --- Store -----------------------------------------------------------------


async def test_store_create_list_revoke(user: User) -> None:
    device, raw_token = await device_store.create_device(user.id, "workstation")
    assert len(raw_token) == 64
    assert device.token_hash == device_store.hash_token(raw_token)
    assert raw_token not in device.token_hash

    listed = await device_store.list_for_user(user.id)
    assert [d.id for d in listed] == [device.id]
    assert await device_store.list_for_user("someone-else") == []

    assert await device_store.get_owned(user.id, device.id) is not None
    assert await device_store.get_owned("someone-else", device.id) is None

    assert await device_store.revoke(user.id, device.id) is not None
    assert await device_store.list_for_user(user.id) == []
    assert await device_store.revoke(user.id, device.id) is None


async def test_store_authenticate(user: User) -> None:
    device, raw_token = await device_store.create_device(user.id, "laptop")
    assert await device_store.authenticate(device.id, raw_token) is not None
    assert await device_store.authenticate(device.id, "wrong") is None
    assert await device_store.authenticate(device.id, "") is None
    assert await device_store.authenticate("no-such-device", raw_token) is None
    await device_store.revoke(user.id, device.id)
    assert await device_store.authenticate(device.id, raw_token) is None


async def test_store_create_rejects_empty_name(user: User) -> None:
    with pytest.raises(ValueError):
        await device_store.create_device(user.id, "   ")


# --- REST -------------------------------------------------------------------


def test_devices_rest_requires_auth() -> None:
    with TestClient(create_app(session_token="test-token")) as client:
        assert client.post("/api/v2/devices", json={"name": "x"}).status_code == 401
        assert client.get("/api/v2/devices").status_code == 401
        assert client.delete("/api/v2/devices/whatever").status_code == 401


def test_devices_rest_crud(session_factory, user: User) -> None:
    with TestClient(create_app(session_token="test-token")) as client:
        resp = client.post("/api/v2/devices", json={"name": "workstation"}, headers=_auth(user))
        assert resp.status_code == 201
        created = resp.json()
        assert created["name"] == "workstation"
        assert len(created["token"]) == 64

        resp = client.get("/api/v2/devices", headers=_auth(user))
        assert resp.status_code == 200
        assert [d["id"] for d in resp.json()] == [created["id"]]
        assert resp.json()[0]["online"] is False

        resp = client.delete(f"/api/v2/devices/{created['id']}", headers=_auth(user))
        assert resp.status_code == 200
        assert client.get("/api/v2/devices", headers=_auth(user)).json() == []
        assert (
            client.delete(f"/api/v2/devices/{created['id']}", headers=_auth(user)).status_code
            == 404
        )


# --- Tunnel WS + relay -------------------------------------------------------


async def _make_device(user: User) -> tuple[str, str]:
    device, raw_token = await device_store.create_device(user.id, "rig")
    return device.id, raw_token


def test_tunnel_rejects_bad_token(session_factory, user: User) -> None:
    device_id, _ = asyncio.run(_make_device(user))
    with TestClient(create_app(session_token="test-token")) as client:
        with (
            pytest.raises(WebSocketDisconnect) as exc_info,
            client.websocket_connect(f"/api/v2/devices/{device_id}/tunnel?token=wrong"),
        ):
            pass
        assert exc_info.value.code == 4401


def test_relay_full_round_trip(session_factory, user: User) -> None:
    device_id, raw_token = asyncio.run(_make_device(user))
    relay_token = tunnel_mod.registry.mint_relay_token("sess-1", device_id, user.id)
    try:
        with (
            TestClient(create_app(session_token="test-token")) as client,
            client.websocket_connect(
                f"/api/v2/devices/{device_id}/tunnel?token={raw_token}"
            ) as ws,
        ):
            # Device shows up as online while the tunnel is attached.
                resp = client.get("/api/v2/devices", headers=_auth(user))
                assert resp.json()[0]["online"] is True

                # Bad relay token -> 401; token bound to another device -> 403.
                assert (
                    client.post(f"/api/v2/devices/{device_id}/mcp", json={"id": 1}).status_code
                    == 401
                )
                other = tunnel_mod.registry.mint_relay_token("sess-2", "other-dev", user.id)
                assert (
                    client.post(
                        f"/api/v2/devices/{device_id}/mcp",
                        json={"id": 1},
                        headers={"Authorization": f"Bearer {other}"},
                    ).status_code
                    == 403
                )

                # Worker side: POST a JSON-RPC request in a thread (it blocks
                # until the device answers over the tunnel).
                result: dict = {}

                def _worker_call() -> None:
                    result["resp"] = client.post(
                        f"/api/v2/devices/{device_id}/mcp",
                        json={"jsonrpc": "2.0", "id": 7, "method": "ping"},
                        headers={"Authorization": f"Bearer {relay_token}"},
                    )

                thread = threading.Thread(target=_worker_call)
                thread.start()

                # Device side: receive the relayed request, answer it.
                request = ws.receive_json()
                assert request["method"] == "ping"
                assert request["id"] != 7  # id rewritten to a tunnel-unique value
                ws.send_json({"jsonrpc": "2.0", "id": request["id"], "result": {}})

                thread.join(timeout=10)
                resp = result["resp"]
                assert resp.status_code == 200
                assert resp.json()["id"] == 7  # original id restored
                assert resp.json()["result"] == {}

                # Notification (no id) -> 202 and is forwarded verbatim.
                resp = client.post(
                    f"/api/v2/devices/{device_id}/mcp",
                    json={"jsonrpc": "2.0", "method": "notifications/initialized"},
                    headers={"Authorization": f"Bearer {relay_token}"},
                )
                assert resp.status_code == 202
                note = ws.receive_json()
                assert note == {"jsonrpc": "2.0", "method": "notifications/initialized"}
    finally:
        tunnel_mod.registry.revoke_session("sess-1")
        tunnel_mod.registry.revoke_session("sess-2")


def test_relay_device_offline(session_factory, user: User) -> None:
    device_id, _ = asyncio.run(_make_device(user))
    relay_token = tunnel_mod.registry.mint_relay_token("sess-9", device_id, user.id)
    try:
        with TestClient(create_app(session_token="test-token")) as client:
            resp = client.post(
                f"/api/v2/devices/{device_id}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
                headers={"Authorization": f"Bearer {relay_token}"},
            )
            assert resp.status_code == 503
            assert resp.json()["detail"] == "Device offline"
    finally:
        tunnel_mod.registry.revoke_session("sess-9")


def test_relay_token_replaced_on_remint() -> None:
    first = tunnel_mod.registry.mint_relay_token("sess-r", "dev", "user")
    second = tunnel_mod.registry.mint_relay_token("sess-r", "dev", "user")
    assert first != second
    assert tunnel_mod.registry.resolve_relay_token(first) is None
    grant = tunnel_mod.registry.resolve_relay_token(second)
    assert grant is not None and grant.session_id == "sess-r"
    tunnel_mod.registry.revoke_session("sess-r")
    assert tunnel_mod.registry.resolve_relay_token(second) is None
