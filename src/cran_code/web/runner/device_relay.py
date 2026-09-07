"""Device-relay env injection for worker subprocesses (ADR 004).

When a session is bound to a Luoshu device (``SessionState.device_id``), the
worker must reach that device through the cloud tunnel relay instead of a
loopback URL it cannot see. This module mints a per-session relay token and
renders the ``CRAN_DEVICE_MCP_CONFIG`` env entry (a fastmcp-format MCP config
fragment) that ``worker.py`` merges into its MCP configs.

The real device token never leaves the web process: the worker only gets the
loopback relay URL + the in-memory relay token.
"""

from __future__ import annotations

import asyncio
import json
import os
from uuid import UUID

from cran_code.utils.logging import logger
from cran_code.web.store.sessions import load_session_by_id
from cran_code.web.tunnel import registry

ENV_DEVICE_MCP_CONFIG = "CRAN_DEVICE_MCP_CONFIG"

DEVICE_SERVER_NAME = "luoshu-device"
"""MCP server name under which the device's tools appear in the session."""


async def device_mcp_env(session_id: UUID) -> dict[str, str]:
    """Return the device-relay env entries for a session, or ``{}``.

    Never raises: device relay must not break session startup.
    """
    try:
        port = os.environ.get("CRAN_WEB_PORT")
        if not port:
            return {}
        joint = await asyncio.to_thread(load_session_by_id, session_id)
        if joint is None:
            return {}
        state = joint.cran_code_session.state
        device_id = getattr(state, "device_id", None)
        if not device_id:
            return {}
        token = registry.mint_relay_token(str(session_id), device_id, state.owner_id)
        config = {
            "mcpServers": {
                DEVICE_SERVER_NAME: {
                    "url": f"http://127.0.0.1:{port}/api/v2/devices/{device_id}/mcp",
                    "transport": "http",
                    "headers": {"Authorization": f"Bearer {token}"},
                }
            }
        }
        return {ENV_DEVICE_MCP_CONFIG: json.dumps(config)}
    except Exception as exc:
        logger.warning(
            "Device relay env injection failed for session {id}: {err}",
            id=session_id,
            err=exc,
        )
        return {}
