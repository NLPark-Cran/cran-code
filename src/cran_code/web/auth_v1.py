"""v1 API auth bridging: resolve v2 JWT or v1 session token into a CurrentUser.

This module provides FastAPI dependencies for v1 endpoints so they can identify
the caller through the same v2 JWT tokens used by the v2 API.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from starlette.websockets import WebSocket

from cran_code.web.auth import parse_bearer_token, verify_token

try:
    from cran_code.web.auth_v2.jwt import decode_token as _decode_v2_token
except Exception:
    _decode_v2_token = None


@dataclass
class CurrentUser:
    """Authenticated user in v1 API context (bridged from v2 JWT or v1 session token)."""

    id: str
    username: str | None = None
    display_name: str | None = None


def extract_token(req_or_ws: Request | WebSocket) -> str | None:
    """Extract bearer token from Authorization header or query param."""
    token = parse_bearer_token(req_or_ws.headers.get("authorization"))
    if token:
        return token
    return req_or_ws.query_params.get("token")


async def resolve_user(token: str | None, app) -> CurrentUser | None:
    """Resolve a token into a CurrentUser."""
    if not token:
        return None
    # v1 session token (anonymous)
    expected = getattr(app.state, "session_token", None)
    if expected and verify_token(token, expected):
        return CurrentUser(id="v1_anonymous", username="anonymous")
    # v2 JWT
    if _decode_v2_token is not None:
        try:
            payload = _decode_v2_token(token)
            if payload.sub:
                # Try to fetch user details from DB
                from cran_code.web.db import AsyncSessionLocal, User
                from sqlalchemy import select

                async with AsyncSessionLocal() as session:
                    result = await session.execute(select(User).where(User.id == payload.sub))
                    user = result.scalar_one_or_none()
                    if user:
                        return CurrentUser(
                            id=user.id,
                            username=user.username,
                            display_name=user.display_name,
                        )
                return CurrentUser(id=payload.sub)
        except Exception:
            pass
    return None


async def get_current_user_v1(request: Request) -> CurrentUser | None:
    """FastAPI dependency: resolve current user from v1 API request."""
    token = extract_token(request)
    return await resolve_user(token, request.app)


async def get_current_user_v1_ws(websocket: WebSocket) -> CurrentUser | None:
    """FastAPI dependency: resolve current user from WebSocket connection."""
    token = extract_token(websocket)
    return await resolve_user(token, websocket.app)
