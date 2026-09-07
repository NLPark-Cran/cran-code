"""Luoshu device registry + reverse tunnel endpoints (ADR 004).

REST (all ``require_user``):
- ``POST   /api/v2/devices``            — register a device; the raw device
  token is returned exactly once in this response.
- ``GET    /api/v2/devices``            — list own devices with online status.
- ``DELETE /api/v2/devices/{id}``       — revoke a device.

Tunnel (device credential, not user JWT):
- ``WS     /api/v2/devices/{id}/tunnel?token=…`` — the Luoshu app connects
  here; MCP JSON-RPC messages flow verbatim in both directions.

Relay (per-session relay token, minted into the worker env):
- ``POST   /api/v2/devices/{id}/mcp``   — a session worker's fastmcp client
  posts MCP JSON-RPC here; it is forwarded over the tunnel.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, cast

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field

from cran_code.utils.logging import logger
from cran_code.web import tunnel as tunnel_mod
from cran_code.web.auth_v2.jwt import User as JWTUser
from cran_code.web.auth_v2.jwt import require_user
from cran_code.web.db import devices as device_store
from cran_code.web.db.models import Device

router = APIRouter(prefix="/api/v2/devices", tags=["devices"])


class DeviceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=device_store.MAX_DEVICE_NAME_LENGTH)


class DeviceCreatedResponse(BaseModel):
    id: str
    name: str
    token: str
    created_at: str


class DeviceResponse(BaseModel):
    id: str
    name: str
    online: bool
    last_seen_at: str | None
    created_at: str


def _device_response(d: Device) -> DeviceResponse:
    return DeviceResponse(
        id=d.id,
        name=d.name,
        online=tunnel_mod.registry.is_online(d.id),
        last_seen_at=d.last_seen_at.isoformat() if d.last_seen_at else None,
        created_at=d.created_at.isoformat(),
    )


@router.post("", response_model=DeviceCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_device(
    request: DeviceCreateRequest,
    current_user: Annotated[JWTUser, Depends(require_user)],
) -> DeviceCreatedResponse:
    """Register a new Luoshu device. Save the returned token: it is shown once."""
    device, raw_token = await device_store.create_device(current_user.id, request.name)
    return DeviceCreatedResponse(
        id=device.id,
        name=device.name,
        token=raw_token,
        created_at=device.created_at.isoformat(),
    )


@router.get("", response_model=list[DeviceResponse])
async def list_devices(
    current_user: Annotated[JWTUser, Depends(require_user)],
) -> list[DeviceResponse]:
    """List the current user's active devices, newest first."""
    devices = await device_store.list_for_user(current_user.id)
    return [_device_response(d) for d in devices]


@router.delete("/{device_id}")
async def revoke_device(
    device_id: str,
    current_user: Annotated[JWTUser, Depends(require_user)],
) -> dict[str, str]:
    """Revoke one of the current user's devices (its token stops working)."""
    device = await device_store.revoke(current_user.id, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    # Kick any live tunnel so revocation takes effect immediately.
    import contextlib

    tunnel = tunnel_mod.registry.tunnel(device_id)
    if tunnel is not None:
        with contextlib.suppress(Exception):
            await tunnel.websocket.close(code=4401, reason="device revoked")
        tunnel_mod.registry.detach(device_id, tunnel)
    return {"detail": "Device revoked"}


def _bearer_token(header_value: str | None) -> str | None:
    if header_value and header_value.startswith("Bearer "):
        return header_value[len("Bearer "):]
    return None


@router.websocket("/{device_id}/tunnel")
async def device_tunnel(device_id: str, websocket: WebSocket) -> None:
    """Reverse-tunnel endpoint: the Luoshu app dials in here (ADR 004).

    Auth is the per-device token (Authorization header or ``?token=``), NOT a
    user JWT — devices are long-lived headless clients.
    """
    token = websocket.query_params.get("token") or _bearer_token(
        websocket.headers.get("authorization")
    )
    device = await device_store.authenticate(device_id, token or "")
    if device is None:
        await websocket.close(code=4401, reason="Invalid device credentials")
        return

    await websocket.accept()
    await device_store.touch_last_seen(device_id)
    tunnel = await tunnel_mod.registry.attach(device_id, websocket)
    logger.info("Device tunnel attached: {id} ({name})", id=device_id, name=device.name)
    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > tunnel_mod.MAX_MESSAGE_BYTES:
                await websocket.close(code=1009, reason="message too large")
                return
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                logger.debug("Device tunnel {id}: dropping non-JSON frame", id=device_id)
                continue
            if isinstance(message, dict):
                tunnel.handle_message(cast(dict[str, Any], message))
    except WebSocketDisconnect:
        pass
    finally:
        tunnel_mod.registry.detach(device_id, tunnel)
        logger.info("Device tunnel detached: {id}", id=device_id)


@router.post("/{device_id}/mcp", response_model=None)
async def device_mcp_relay(device_id: str, request: Request) -> Any:
    """Relay one MCP JSON-RPC message to the device over its tunnel.

    Authenticated by a per-session relay token (minted into the worker env as
    ``CRAN_DEVICE_MCP_CONFIG``); the real device token never leaves this
    process. Notification messages (no ``id``) get a bare 202, matching the
    loopback bridge's Streamable HTTP semantics.
    """
    token = _bearer_token(request.headers.get("authorization"))
    grant = tunnel_mod.registry.resolve_relay_token(token)
    if grant is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid relay token",
        )
    if grant.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Relay token is not bound to this device",
        )
    tunnel = tunnel_mod.registry.tunnel(device_id)
    if tunnel is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device offline",
        )

    body = await request.body()
    if len(body) > tunnel_mod.MAX_MESSAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Message too large",
        )
    try:
        message = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON-RPC payload",
        ) from exc
    if not isinstance(message, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON-RPC payload",
        )
    message = cast(dict[str, Any], message)

    await device_store.touch_last_seen(device_id)
    try:
        response = await tunnel.call(message)
    except tunnel_mod.DeviceOfflineError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device offline",
        ) from exc
    except tunnel_mod.TunnelTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Device did not respond in time",
        ) from exc
    if response is None:
        # Notification: 202 with no body, matching the loopback bridge.
        return Response(status_code=status.HTTP_202_ACCEPTED)
    return response
