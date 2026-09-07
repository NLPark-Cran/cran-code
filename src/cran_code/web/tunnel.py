"""In-memory registry for Luoshu device reverse tunnels (ADR 004).

One WebSocket per device: the cloud relays MCP JSON-RPC messages to the
device verbatim and awaits the matching response. Request ``id`` values are
rewritten to tunnel-unique ids (``t-<n>``) before forwarding because
concurrent fastmcp clients each count from 1 and would otherwise collide;
the original id is restored on the way back. Device-side notifications are
forwarded without tracking.

Also mints/resolves per-session *relay tokens*: short-lived in-memory
credentials that let a session's worker subprocess POST MCP calls to
``/api/v2/devices/{id}/mcp`` without ever seeing the real device token.

Everything lives in the web process memory: a restart simply marks all
devices offline until their tunnels reconnect (devices retry with backoff).
"""

from __future__ import annotations

import asyncio
import contextlib
import itertools
import json
import secrets
from dataclasses import dataclass
from typing import Any

from starlette.websockets import WebSocket

from cran_code.utils.logging import logger

MAX_MESSAGE_BYTES = 4 * 1024 * 1024
"""Matches the loopback bridge's HTTP body limit."""

CALL_TIMEOUT_SECONDS = 120.0
"""Upper bound for one relayed call (bridge tools cap themselves at 30s)."""

CLOSE_REPLACED = 4000
"""Close code: this device opened a newer tunnel connection."""


class DeviceOfflineError(RuntimeError):
    """No live tunnel for the requested device."""


class TunnelTimeoutError(TimeoutError):
    """The device did not answer a relayed call in time."""


@dataclass
class RelayGrant:
    session_id: str
    device_id: str
    owner_id: str | None


class DeviceTunnel:
    """One live device WebSocket plus its in-flight relayed calls."""

    def __init__(self, device_id: str, websocket: WebSocket) -> None:
        self.device_id = device_id
        self.websocket = websocket
        self._send_lock = asyncio.Lock()
        self._pending: dict[str, tuple[Any, asyncio.Future[dict[str, Any]]]] = {}
        self._counter = itertools.count(1)
        self.closed = False

    async def call(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Forward one JSON-RPC message; returns the response, or None for
        notifications (no ``id``). Raises DeviceOfflineError/TunnelTimeoutError."""
        if self.closed:
            raise DeviceOfflineError(f"device {self.device_id} tunnel is closed")
        msg_id = message.get("id")
        if msg_id is None:
            async with self._send_lock:
                await self.websocket.send_text(json.dumps(message, ensure_ascii=False))
            return None

        tunnel_id = f"t-{next(self._counter)}"
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[tunnel_id] = (msg_id, future)
        outbound = dict(message)
        outbound["id"] = tunnel_id
        try:
            async with self._send_lock:
                await self.websocket.send_text(json.dumps(outbound, ensure_ascii=False))
            response = await asyncio.wait_for(future, timeout=CALL_TIMEOUT_SECONDS)
        except TimeoutError as exc:
            raise TunnelTimeoutError(
                f"device {self.device_id} did not respond within {CALL_TIMEOUT_SECONDS:.0f}s"
            ) from exc
        finally:
            self._pending.pop(tunnel_id, None)
        response = dict(response)
        response["id"] = msg_id
        return response

    def handle_message(self, message: dict[str, Any]) -> None:
        """Route an inbound device message to its waiting caller, if any."""
        msg_id = message.get("id")
        if msg_id is None or ("result" not in message and "error" not in message):
            # Requests/notifications initiated by the device are not part of
            # the protocol (v1 is cloud-driven only); ignore defensively.
            return
        entry = self._pending.get(str(msg_id))
        if entry is None:
            logger.debug(
                "Device tunnel {id}: response for unknown id {mid}",
                id=self.device_id,
                mid=msg_id,
            )
            return
        _, future = entry
        if not future.done():
            future.set_result(message)

    def fail_all(self, exc: BaseException) -> None:
        """Fail every in-flight call (tunnel closed or replaced)."""
        for _, future in self._pending.values():
            if not future.done():
                future.set_exception(exc)


class TunnelRegistry:
    """Process-wide registry of live device tunnels and relay tokens."""

    def __init__(self) -> None:
        self._tunnels: dict[str, DeviceTunnel] = {}
        self._relay_tokens: dict[str, RelayGrant] = {}
        self._session_tokens: dict[str, str] = {}

    async def attach(self, device_id: str, websocket: WebSocket) -> DeviceTunnel:
        """Register a new tunnel, replacing (and closing) any stale one."""
        old = self._tunnels.get(device_id)
        tunnel = DeviceTunnel(device_id, websocket)
        self._tunnels[device_id] = tunnel
        if old is not None:
            old.closed = True
            old.fail_all(DeviceOfflineError("tunnel replaced by a newer connection"))
            with contextlib.suppress(Exception):
                await old.websocket.close(code=CLOSE_REPLACED, reason="replaced")
        return tunnel

    def detach(self, device_id: str, tunnel: DeviceTunnel) -> None:
        """Remove a tunnel if it is still the registered one for the device."""
        if self._tunnels.get(device_id) is tunnel:
            del self._tunnels[device_id]
        tunnel.closed = True
        tunnel.fail_all(DeviceOfflineError(f"device {device_id} disconnected"))

    def is_online(self, device_id: str) -> bool:
        return device_id in self._tunnels

    def tunnel(self, device_id: str) -> DeviceTunnel | None:
        return self._tunnels.get(device_id)

    # --- Relay tokens -----------------------------------------------------

    def mint_relay_token(
        self, session_id: str, device_id: str, owner_id: str | None
    ) -> str:
        """Mint a relay token for a session's worker; re-minting replaces the
        previous token of that session (worker restarts re-mint)."""
        old = self._session_tokens.pop(session_id, None)
        if old is not None:
            self._relay_tokens.pop(old, None)
        token = secrets.token_hex(32)
        self._relay_tokens[token] = RelayGrant(
            session_id=session_id, device_id=device_id, owner_id=owner_id
        )
        self._session_tokens[session_id] = token
        return token

    def resolve_relay_token(self, token: str | None) -> RelayGrant | None:
        if not token:
            return None
        return self._relay_tokens.get(token)

    def revoke_session(self, session_id: str) -> None:
        token = self._session_tokens.pop(session_id, None)
        if token is not None:
            self._relay_tokens.pop(token, None)


registry = TunnelRegistry()
