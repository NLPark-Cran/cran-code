"""Real-time collaboration WebSocket for Yjs."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from cran_code.web.auth_v2.jwt import User as JWTUser, require_user
from cran_code.web.db import AsyncSessionLocal, Project, TeamMember

router = APIRouter(prefix="/api/v2/projects", tags=["collab"])

_rooms: dict[str, set[WebSocket]] = {}
_locks: dict[str, asyncio.Lock] = {}


async def _get_room_lock(room_id: str) -> asyncio.Lock:
    if room_id not in _locks:
        _locks[room_id] = asyncio.Lock()
    return _locks[room_id]


@router.websocket("/{project_id}/collab")
async def collab_websocket(
    websocket: WebSocket,
    project_id: str,
    token: str | None = None,
) -> None:
    from cran_code.web.auth_v2.jwt import decode_token

    current_user: JWTUser | None = None
    if token:
        try:
            payload = decode_token(token)
            from cran_code.web.db import User
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(User).where(User.id == payload.sub))
                user = result.scalar_one_or_none()
                if user is not None and user.is_active:
                    current_user = JWTUser(
                        id=user.id,
                        email=user.email,
                        username=user.username,
                        display_name=user.display_name,
                        avatar_url=user.avatar_url,
                        role=user.role,
                        created_at=user.created_at,
                    )
        except Exception:
            pass

    if current_user is None:
        await websocket.close(code=4401, reason="Authentication required")
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if project is None:
            await websocket.close(code=4404, reason="Project not found")
            return

        team_member = await session.execute(
            select(TeamMember).where(
                (TeamMember.team_id == project.team_id) & (TeamMember.user_id == current_user.id)
            )
        )
        if team_member.scalar_one_or_none() is None:
            await websocket.close(code=4403, reason="Not a team member")
            return

    room_id = f"project:{project_id}"
    lock = await _get_room_lock(room_id)

    await websocket.accept()
    async with lock:
        if room_id not in _rooms:
            _rooms[room_id] = set()
        _rooms[room_id].add(websocket)

    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            if "bytes" in message:
                data = message["bytes"]
                # Try to detect if it's an awareness JSON message
                try:
                    text = data.decode("utf-8")
                    msg = json.loads(text)
                    if isinstance(msg, dict) and msg.get("type") == "awareness":
                        async with lock:
                            peers = [c for c in _rooms.get(room_id, set()) if c is not websocket]
                        for client in peers:
                            try:
                                await client.send_bytes(data)
                            except Exception:
                                pass
                        continue
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
                # Yjs binary update
                async with lock:
                    peers = [c for c in _rooms.get(room_id, set()) if c is not websocket]
                for client in peers:
                    try:
                        await client.send_bytes(data)
                    except Exception:
                        pass
            elif "text" in message:
                data = message["text"]
                # Awareness or other JSON messages
                async with lock:
                    peers = [c for c in _rooms.get(room_id, set()) if c is not websocket]
                for client in peers:
                    try:
                        await client.send_text(data)
                    except Exception:
                        pass
    except WebSocketDisconnect:
        pass
    finally:
        async with lock:
            room = _rooms.get(room_id)
            if room:
                room.discard(websocket)
                if not room:
                    del _rooms[room_id]
                    if room_id in _locks:
                        del _locks[room_id]
