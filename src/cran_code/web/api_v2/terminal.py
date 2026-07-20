"""Integrated terminal WebSocket for projects."""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
from pathlib import Path

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select

from cran_code.web.auth_v2.jwt import User as JWTUser, require_user
from cran_code.web.db import AsyncSessionLocal, Project, TeamMember
from cran_code.utils.subprocess_env import get_clean_env

router = APIRouter(prefix="/api/v2/projects", tags=["terminal"])

_PROJECT_ROOT = Path(
    os.environ.get("CRAN_PROJECT_ROOT", str(Path.home()))
).expanduser().resolve()


@router.websocket("/{project_id}/terminal")
async def terminal_websocket(
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

        work_dir = project.work_dir
        if not work_dir:
            await websocket.close(code=4400, reason="Project has no working directory")
            return

    cwd = Path(work_dir).expanduser().resolve()
    try:
        cwd.relative_to(_PROJECT_ROOT)
    except ValueError:
        await websocket.close(code=4403, reason="Project directory outside allowed root")
        return
    if not cwd.exists():
        await websocket.close(code=4400, reason="Working directory does not exist")
        return

    await websocket.accept()

    # Spawn a shell subprocess with sanitized environment
    shell = os.environ.get("SHELL", "/bin/bash")
    allowed_env_keys = {"PATH", "HOME", "USER", "SHELL", "TERM", "LANG", "LC_ALL", "EDITOR", "FORCE_COLOR"}
    base_env = {k: v for k, v in os.environ.items() if k in allowed_env_keys}
    proc = await asyncio.create_subprocess_exec(
        shell,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd,
        env=get_clean_env(base_env={**base_env, "TERM": "xterm-256color", "FORCE_COLOR": "1"}),
    )

    async def read_stdout() -> None:
        try:
            while True:
                chunk = await proc.stdout.read(4096)
                if not chunk:
                    break
                try:
                    await websocket.send_text(chunk.decode("utf-8", errors="replace"))
                except Exception:
                    break
        except Exception:
            pass

    read_task = asyncio.create_task(read_stdout())

    try:
        while True:
            message = await websocket.receive_text()
            if proc.stdin and not proc.stdin.is_closing():
                proc.stdin.write(message.encode("utf-8"))
                await proc.stdin.drain()
    except WebSocketDisconnect:
        pass
    finally:
        read_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await read_task
        if proc.returncode is None:
            proc.send_signal(signal.SIGHUP)
            try:
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except TimeoutError:
                proc.kill()
                await proc.wait()
