"""JSON-RPC message helpers for Kimi CLI web interface."""

from typing import Any, Literal
from uuid import uuid4

from fastapi import WebSocket
from pydantic import BaseModel, ConfigDict
from starlette.websockets import WebSocketState

from cran_code.web.models import SessionStatus


class _MessageBase(BaseModel):
    """Base model for JSON-RPC messages."""

    jsonrpc: Literal["2.0"] = "2.0"
    model_config = ConfigDict(extra="forbid")


class JSONRPCSessionStatusMessage(_MessageBase):
    """Session status update message."""

    method: Literal["session_status"] = "session_status"
    params: SessionStatus


class JSONRPCHistoryCompleteMessage(_MessageBase):
    """Sent after history replay, before environment is ready."""

    method: Literal["history_complete"] = "history_complete"
    id: str
    params: dict | None = None
    """Pagination info: ``{"has_more_history": bool, "oldest_line": int}``."""


def new_session_status_message(status: SessionStatus) -> JSONRPCSessionStatusMessage:
    """Create a new session status message."""
    return JSONRPCSessionStatusMessage(params=status)


def new_history_complete_message(
    *, has_more_history: bool = False, oldest_line: int = 0
) -> JSONRPCHistoryCompleteMessage:
    """Create a new history complete message."""
    return JSONRPCHistoryCompleteMessage(
        id=str(uuid4()),
        params={"has_more_history": has_more_history, "oldest_line": oldest_line},
    )


async def send_history_complete(ws: WebSocket, page: Any = None) -> bool:
    """Send history complete message to a WebSocket.

    Returns:
        True if message was sent successfully, False if the send fails or the WebSocket is not
        connected.
    """
    if ws.client_state != WebSocketState.CONNECTED:
        return False
    try:
        has_more = bool(page is not None and getattr(page, "has_more", False))
        oldest = int(getattr(page, "oldest_line", 0) or 0) if page is not None else 0
        await ws.send_text(
            new_history_complete_message(
                has_more_history=has_more, oldest_line=oldest
            ).model_dump_json()
        )
        return True
    except Exception:
        return False
