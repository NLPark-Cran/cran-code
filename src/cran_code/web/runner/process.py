"""Session process management for Kimi CLI web interface."""

from __future__ import annotations

import asyncio
import base64
import contextlib
import io
import json
import mimetypes
import os
import sys
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from kosong.chat_provider import TokenUsage
from kosong.message import ContentPart, ImageURLPart, TextPart
from PIL import Image
from PIL.Image import Image as PILImage
from pydantic import TypeAdapter
from starlette.websockets import WebSocket, WebSocketState

from cran_code import logger
from cran_code.config import load_config
from cran_code.llm import ModelCapability
from cran_code.utils.subprocess_env import get_clean_env
from cran_code.web.models import (
    SessionNoticeEvent,
    SessionNoticePayload,
    SessionState,
    SessionStatus,
)
from cran_code.web.runner.messages import new_session_status_message
from cran_code.web.store.sessions import load_session_by_id
from cran_code.wire.file import WireFile
from cran_code.wire.types import (
    CompactionBegin,
    CompactionEnd,
    CompactionSummary,
    ContentPart as WireContentPart,
    StatusUpdate,
    TurnBegin,
)
from cran_code.wire.jsonrpc import (
    JSONRPCCancelMessage,
    JSONRPCErrorObject,
    JSONRPCErrorResponse,
    JSONRPCEventMessage,
    JSONRPCInMessage,
    JSONRPCInMessageAdapter,
    JSONRPCInitializeMessage,
    JSONRPCOutMessage,
    JSONRPCPromptMessage,
    JSONRPCRequestMessage,
    JSONRPCSuccessResponse,
)
from cran_code.wire.serde import deserialize_wire_message

JSONRPCOutMessageAdapter = TypeAdapter[JSONRPCOutMessage](JSONRPCOutMessage)

# Env vars that must never leak into worker processes: workers run the
# agent's Shell tool with their full environment, so web-server secrets
# (JWT signing key, session token, database URL) must be stripped here.
_BLOCKED_WORKER_ENV_VARS = {
    "CRAN_JWT_SECRET",
    "CRAN_WEB_SESSION_TOKEN",
    "CRAN_DATABASE_URL",
}

# Provider credential / endpoint env vars: stripped so a server-side value can
# never silently override per-user key resolution; targeted injection in
# _build_worker_env re-adds the right ones.
_BLOCKED_PROVIDER_ENV_VARS = {
    "CRAN_API_KEY",
    "CRAN_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
}


def _sanitize_worker_env(env: dict[str, str]) -> dict[str, str]:
    """Remove web-server secrets and provider credentials from worker env."""
    return {
        k: v
        for k, v in env.items()
        if k not in _BLOCKED_WORKER_ENV_VARS
        and k not in _BLOCKED_PROVIDER_ENV_VARS
        and not (k.startswith("CRAN_") and k.endswith(("_SECRET", "_SECRET_KEY")))
    }


@dataclass
class _SessionKeyInfo:
    """Key resolution snapshot for a session's current default model."""

    owner_id: str
    provider_key: str
    provider_type: str
    model: str
    has_global_key: bool
    api_key: str = ""
    """Resolved key material; empty when no key is usable for this user."""
    source: str = ""
    """""personal" | "team" | "shared"; empty when unresolved."""


class SessionProcess:
    """Manages a single session's KimiCLI subprocess.

    Handles:
    - Starting/stopping the subprocess
    - Reading from stdout (wire messages from KimiCLI)
    - Writing to stdin (user input to KimiCLI)
    - Broadcasting messages to connected WebSockets

    Concurrency model:
    - `SessionProcess` is the long-lived container for a `session_id`.
      It may outlive worker restarts.
    - Liveness vs busy are separate:
      - `is_alive` / `is_running`: worker subprocess exists and has not exited.
      - `is_busy`: there is at least one in-flight prompt id.
    - WebSocket fanout supports "join while running":
      - New clients replay `wire.jsonl` history first.
      - Live messages during replay are buffered per-WS and flushed afterwards.

    Locks:
    - `_lock` guards worker lifecycle and busy state.
    - `_ws_lock` guards WebSocket state.
    """

    def __init__(self, session_id: UUID) -> None:
        """Initialize a session process."""
        self.session_id = session_id
        self._in_flight_prompt_ids: set[str] = set()
        self._status_seq = 0
        self._worker_id: str | None = None
        self._status = SessionStatus(
            session_id=self.session_id,
            state="stopped",
            seq=self._status_seq,
            worker_id=self._worker_id,
            reason=None,
            detail=None,
            updated_at=datetime.now(UTC),
        )
        self._process: asyncio.subprocess.Process | None = None
        self._websockets: set[WebSocket] = set()
        self._websocket_count = 0
        self._replay_buffers: dict[WebSocket, list[str]] = {}
        self._read_task: asyncio.Task[None] | None = None
        self._expecting_exit = False
        self._lock = asyncio.Lock()
        self._ws_lock = asyncio.Lock()
        self._sent_files: set[str] = set()
        self._annotated_wire_file: WireFile | None = None
        self._in_compaction: bool = False
        self._compaction_buffer: list[tuple[WireMessage, float]] = []
        # Latest initialize message received from a client, cached so it can be
        # replayed to a freshly spawned worker. Worker restarts keep client
        # WebSockets alive, so the client never re-sends initialize and the new
        # wire server would otherwise lose client capabilities (e.g.
        # supports_question) — leaving AskUserQuestion visible but unusable.
        self._cached_initialize_message: str | None = None
        # The initialize message most recently replayed by start(), used to
        # avoid writing the same message twice when it triggered the spawn.
        self._replayed_initialize_message: str | None = None
        # Whether the current worker generation already received an initialize
        # (via replay or a forwarded client message). Multi-client sessions
        # resend initialize on worker_id change; only the first may pass.
        self._worker_initialized: bool = False
        # Latest key-resolution snapshot (per worker spawn), used for usage
        # metering of direct-injected personal keys.
        self._key_info: _SessionKeyInfo | None = None

    def _get_annotated_wire_file(self) -> WireFile | None:
        """Lazy-load the annotated wire file for this session."""
        if self._annotated_wire_file is not None:
            return self._annotated_wire_file
        session = load_session_by_id(self.session_id)
        if session is None or not session.session_dir:
            return None
        annotated_path = Path(session.session_dir) / "wire.annotated.jsonl"
        self._annotated_wire_file = WireFile(annotated_path)
        return self._annotated_wire_file

    @property
    def is_alive(self) -> bool:
        """Whether the worker subprocess exists and has not exited."""
        process = self._process
        return process is not None and process.returncode is None

    @property
    def is_running(self) -> bool:
        """Backward-compatible name: indicates worker liveness."""
        return self.is_alive

    @property
    def is_busy(self) -> bool:
        """Whether the session is currently processing a prompt."""
        return len(self._in_flight_prompt_ids) > 0

    def clear_in_flight(self) -> None:
        """Clear stale in-flight prompt IDs (e.g. after an error)."""
        self._in_flight_prompt_ids.clear()

    @property
    def status(self) -> SessionStatus:
        """Current runtime status snapshot."""
        return self._status

    @property
    def websocket_count(self) -> int:
        """Get the number of connected WebSockets."""
        return self._websocket_count

    async def send_status_snapshot(self, ws: WebSocket) -> None:
        """Send the current status snapshot to a specific WebSocket."""
        await ws.send_text(new_session_status_message(self._status).model_dump_json())

    def _build_status(
        self,
        state: SessionState,
        reason: str | None,
        detail: str | None,
    ) -> SessionStatus | None:
        """Build a new status object if different from current."""
        current = self._status
        if (
            current.state == state
            and current.reason == reason
            and current.detail == detail
            and current.worker_id == self._worker_id
        ):
            return None
        self._status_seq += 1
        status = SessionStatus(
            session_id=self.session_id,
            state=state,
            seq=self._status_seq,
            worker_id=self._worker_id,
            reason=reason,
            detail=detail,
            updated_at=datetime.now(UTC),
        )
        self._status = status
        return status

    async def _emit_status(
        self,
        state: SessionState,
        *,
        reason: str | None = None,
        detail: str | None = None,
    ) -> None:
        """Emit a status update if different from current."""
        status = self._build_status(state, reason, detail)
        if status is None:
            return
        await self._broadcast(new_session_status_message(status).model_dump_json())

    async def _resolve_session_key(self) -> _SessionKeyInfo | None:
        """Resolve the provider key for this session's owner and default model.

        Returns ``None`` for legacy/anonymous sessions (no owner), and an info
        object with empty ``api_key``/``source`` when the owner has no usable
        key for the provider.
        """
        session = load_session_by_id(self.session_id)
        owner_id = session.cran_code_session.state.owner_id if session else None
        if not owner_id or owner_id in ("local", "v1_anonymous"):
            return None
        config = load_config()
        model = config.models.get(config.default_model)
        if model is None:
            return None
        provider = config.providers.get(model.provider)
        if provider is None:
            return None

        from cran_code.web.api_v2.keyproxy import _user_team_ids
        from cran_code.web.db.keys import resolve_provider_key

        team_ids = await _user_team_ids(owner_id)
        resolved = await resolve_provider_key(owner_id, model.provider, team_ids)
        info = _SessionKeyInfo(
            owner_id=owner_id,
            provider_key=model.provider,
            provider_type=provider.type,
            model=model.model,
            has_global_key=bool(provider.api_key.get_secret_value()),
        )
        if resolved is not None:
            info.api_key, info.source = resolved
        return info

    async def _build_worker_env(self) -> dict[str, str]:
        """Build the environment for a new worker subprocess.

        Starts from the sanitized server env (web secrets stripped), then
        injects the session owner's provider credentials:

        - personal keys are injected directly (the user owns them anyway);
        - team/shared keys for OpenAI-compatible providers are routed through
          the local key proxy (``/px/v1``) with a signed ``cwk_`` token so the
          worker never sees the real key;
        - kimi providers keep the config.toml/OAuth flow for non-personal
          sources.
        """
        env = _sanitize_worker_env(get_clean_env())
        self._key_info = None
        try:
            info = await self._resolve_session_key()
        except Exception as e:
            logger.warning(f"Key resolution failed for session {self.session_id}: {e}")
            return env
        self._key_info = info
        if info is None or not info.api_key:
            return env
        proxy_url = self._key_proxy_url()
        if info.provider_type == "kimi":
            if info.source == "personal":
                env["CRAN_API_KEY"] = info.api_key
            elif proxy_url:
                # Team/shared kimi keys go through the proxy as well so quota
                # enforcement and usage metering apply (OAuth-managed kimi
                # providers have no resolvable key and never reach this path).
                from cran_code.web.api_v2.keyproxy import mint_proxy_token

                env["CRAN_BASE_URL"] = proxy_url
                env["CRAN_API_KEY"] = mint_proxy_token(
                    info.owner_id, info.provider_key, info.source
                )
        elif info.provider_type in ("openai_legacy", "openai_responses"):
            if info.source == "personal":
                env["OPENAI_API_KEY"] = info.api_key
            elif proxy_url:
                from cran_code.web.api_v2.keyproxy import mint_proxy_token

                env["OPENAI_BASE_URL"] = proxy_url
                env["OPENAI_API_KEY"] = mint_proxy_token(
                    info.owner_id, info.provider_key, info.source
                )
        # Other provider types (anthropic/google/...) have no env-override
        # channel in augment_provider_with_env_vars; they use config as-is.
        return env

    @staticmethod
    def _key_proxy_url() -> str | None:
        port = os.environ.get("CRAN_KEY_PROXY_PORT")
        return f"http://127.0.0.1:{port}/px/v1" if port else None

    async def start(
        self,
        *,
        reason: str | None = None,
        detail: str | None = None,
        restart_started_at: float | None = None,
    ) -> None:
        """Start the KimiCLI subprocess."""
        async with self._lock:
            await self._start_locked(
                reason=reason, detail=detail, restart_started_at=restart_started_at
            )

    async def _start_locked(
        self,
        *,
        reason: str | None = None,
        detail: str | None = None,
        restart_started_at: float | None = None,
    ) -> None:
        """Start the worker subprocess. Caller must hold ``self._lock``."""
        if self.is_alive:
            if self._read_task is None or self._read_task.done():
                self._read_task = asyncio.create_task(self._read_loop())
            return

        self._in_flight_prompt_ids.clear()
        self._expecting_exit = False
        self._worker_id = str(uuid4())

        # 16MB buffer for large messages (e.g., base64-encoded images)
        STREAM_LIMIT = 16 * 1024 * 1024

        if getattr(sys, "frozen", False):
            worker_cmd = [sys.executable, "__web-worker", str(self.session_id)]
        else:
            worker_cmd = [
                sys.executable,
                "-m",
                "cran_code.web.runner.worker",
                str(self.session_id),
            ]

        self._process = await asyncio.create_subprocess_exec(
            *worker_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=STREAM_LIMIT,
            env=await self._build_worker_env(),
        )

        self._read_task = asyncio.create_task(self._read_loop())

        # Replay the client's cached initialize message so the fresh wire
        # server restores client capabilities (supports_question,
        # supports_plan_mode), client info, external tools and hooks.
        self._replayed_initialize_message = None
        self._worker_initialized = False
        if self._cached_initialize_message is not None:
            assert self._process.stdin is not None
            self._process.stdin.write(
                (self._cached_initialize_message + "\n").encode("utf-8")
            )
            await self._process.stdin.drain()
            self._replayed_initialize_message = self._cached_initialize_message
            self._worker_initialized = True

        if restart_started_at is not None:
            elapsed_ms = int((time.perf_counter() - restart_started_at) * 1000)
            detail = f"restart_ms={elapsed_ms}"
            await self._emit_status("idle", reason=reason or "start", detail=detail)
            await self._emit_restart_notice(reason=reason, restart_ms=elapsed_ms)
        else:
            await self._emit_status("idle", reason=reason or "start", detail=None)

    async def stop(self) -> None:
        """Stop the session: terminate worker and close all WebSockets."""
        await self.stop_worker(reason="stop")
        await self._close_all_websockets()

    async def stop_worker(
        self,
        *,
        reason: str | None = None,
        emit_status: bool = True,
    ) -> None:
        """Stop only the worker subprocess, keeping WebSockets connected."""
        async with self._lock:
            await self._stop_worker_locked(reason=reason, emit_status=emit_status)

    async def _stop_worker_locked(
        self,
        *,
        reason: str | None = None,
        emit_status: bool = True,
    ) -> None:
        """Stop the worker subprocess. Caller must hold ``self._lock``."""
        self._expecting_exit = True
        if self._process is not None:
            if self._process.returncode is None:
                self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=10.0)
            except TimeoutError:
                self._process.kill()
                await self._process.wait()
            self._process = None

        if self._read_task is not None:
            self._read_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._read_task
            self._read_task = None

        self._in_flight_prompt_ids.clear()
        self._worker_id = None
        self._expecting_exit = False
        if emit_status:
            await self._emit_status("stopped", reason=reason or "stop")

    async def restart_worker(self, *, reason: str | None = None, force: bool = False) -> bool:
        """Restart the worker subprocess without disconnecting WebSockets.

        Returns True when the worker was restarted, False when skipped because
        the session is busy and ``force`` is not set. The busy check and the
        stop/start sequence happen under the session lock so prompts cannot
        interleave mid-restart.
        """
        async with self._lock:
            if self.is_busy and not force:
                return False
            started_at = time.perf_counter()
            await self._emit_status("restarting", reason=reason or "restart")
            await self._stop_worker_locked(reason="restart", emit_status=False)
            await self._start_locked(reason=reason or "restart", restart_started_at=started_at)
            return True

    async def _emit_restart_notice(self, *, reason: str | None, restart_ms: int) -> None:
        """Emit a restart notice to all WebSockets."""
        label = "Session restarted"
        if reason == "config_update":
            label = "Session restarted due to config update"
        payload = SessionNoticePayload(
            text=f"{label} · {restart_ms}ms",
            kind="restart",
            reason=reason,
            restart_ms=restart_ms,
        )
        event = SessionNoticeEvent(payload=payload)
        await self._broadcast(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "event",
                    "params": event.model_dump(mode="json"),
                },
                ensure_ascii=False,
            )
        )

    async def _read_loop(self) -> None:
        """Read messages from subprocess stdout and broadcast to WebSockets."""
        assert self._process is not None
        assert self._process.stdout is not None
        assert self._process.stderr is not None

        try:
            while True:
                line = await self._process.stdout.readline()
                if not line:
                    if self._process.stdout.at_eof():
                        if self._expecting_exit:
                            break

                        # Wait briefly for the process to actually exit and for
                        # stderr to drain.  Use bounded waits so a stuck pipe
                        # cannot block the whole session manager forever.
                        try:
                            await asyncio.wait_for(
                                self._process.wait(), timeout=10.0
                            )
                        except TimeoutError:
                            with contextlib.suppress(Exception):
                                self._process.kill()
                            with contextlib.suppress(Exception):
                                await asyncio.wait_for(
                                    self._process.wait(), timeout=5.0
                                )

                        try:
                            stderr = await asyncio.wait_for(
                                self._process.stderr.read(), timeout=5.0
                            )
                        except TimeoutError:
                            stderr = b""

                        # Build a human-friendly message instead of the cryptic
                        # "No stderr" when the worker dies without logging.
                        stderr_text = stderr.decode("utf-8", errors="replace")
                        if not stderr_text.strip():
                            rc = self._process.returncode
                            if rc is None or rc < 0:
                                sig = -rc if isinstance(rc, int) and rc < 0 else 9
                                stderr_text = (
                                    f"Worker process was terminated unexpectedly "
                                    f"(signal {sig}, possibly OOM killed). "
                                    f"No stderr captured."
                                )
                            else:
                                stderr_text = (
                                    f"Worker process exited with code {rc}. "
                                    f"No stderr captured."
                                )

                        # Clear in-flight IDs before broadcasting so that
                        # is_busy is already False when the frontend reacts
                        # to the error and sends a new prompt.
                        self._in_flight_prompt_ids.clear()
                        await self._broadcast(
                            JSONRPCErrorResponse(
                                id=str(uuid4()),
                                error=JSONRPCErrorObject(
                                    code=self._process.returncode or -1,
                                    message=stderr_text,
                                ),
                            ).model_dump_json()
                        )
                        logger.warning(
                            f"Process exited with {self._process.returncode}: "
                            f"{stderr_text}"
                        )
                        await self._emit_status(
                            "error",
                            reason="process_exit",
                            detail=stderr_text,
                        )
                        break
                    else:
                        continue

                await self._broadcast(line.decode("utf-8", errors="replace").rstrip("\n"))

                # Handle out message
                try:
                    msg = json.loads(line)
                    match msg.get("method"):
                        case "event":
                            wire_msg = deserialize_wire_message(msg["params"])
                            msg["params"] = wire_msg
                            await self._handle_out_message(JSONRPCEventMessage.model_validate(msg))
                            # Usage metering for direct-injected personal keys
                            # (team/shared usage is recorded by the key proxy).
                            if isinstance(wire_msg, StatusUpdate) and wire_msg.token_usage is not None:
                                await self._record_wire_usage(wire_msg.token_usage)
                            # Compaction tracking
                            if isinstance(wire_msg, CompactionBegin):
                                self._in_compaction = True
                                self._compaction_buffer.clear()
                            elif isinstance(wire_msg, CompactionEnd):
                                self._in_compaction = False
                                annotated = self._get_annotated_wire_file()
                                if annotated is not None and self._compaction_buffer:
                                    human_turns: list[dict[str, Any]] = []
                                    ai_turns: list[dict[str, Any]] = []
                                    for buf_msg, buf_ts in self._compaction_buffer:
                                        if isinstance(buf_msg, TurnBegin):
                                            excerpt = ""
                                            if isinstance(buf_msg.user_input, str):
                                                excerpt = buf_msg.user_input[:80]
                                            elif isinstance(buf_msg.user_input, list) and buf_msg.user_input:
                                                first = buf_msg.user_input[0]
                                                if hasattr(first, "text"):
                                                    excerpt = first.text[:80]
                                            human_turns.append({
                                                "author": "User",
                                                "timestamp": buf_ts,
                                                "excerpt": excerpt,
                                            })
                                        elif isinstance(buf_msg, WireContentPart) and buf_msg.type == "text":
                                            text = getattr(buf_msg, "text", "")[:80]
                                            ai_turns.append({
                                                "timestamp": buf_ts,
                                                "summary": text,
                                            })
                                    summary = CompactionSummary(
                                        human_turns=human_turns,
                                        ai_turns=ai_turns,
                                    )
                                    try:
                                        await annotated.append_message(summary, author="system")
                                    except Exception:
                                        pass
                                    # Broadcast CompactionSummary to WebSockets so the UI can show a timeline
                                    try:
                                        summary_event = JSONRPCEventMessage(params=summary)
                                        await self._broadcast(summary_event.model_dump_json())
                                    except Exception:
                                        pass
                                self._compaction_buffer.clear()
                            elif self._in_compaction:
                                self._compaction_buffer.append((wire_msg, time.time()))
                            # Write to annotated wire file with AI/tool author
                            elif not isinstance(wire_msg, TurnBegin):
                                annotated = self._get_annotated_wire_file()
                                if annotated is not None:
                                    author = "tool" if type(wire_msg).__name__ == "ToolResult" else "AI"
                                    try:
                                        await annotated.append_message(wire_msg, author=author)
                                    except Exception:
                                        pass
                        case "request":
                            wire_msg = deserialize_wire_message(msg["params"])
                            msg["params"] = wire_msg
                            await self._handle_out_message(
                                JSONRPCRequestMessage.model_validate(msg)
                            )
                        case _:
                            if msg.get("error"):
                                await self._handle_out_message(
                                    JSONRPCErrorResponse.model_validate(msg)
                                )
                            else:
                                await self._handle_out_message(
                                    JSONRPCSuccessResponse.model_validate(msg)
                                )
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSONRPC out message: {line}")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Unexpected error in read loop: {e.__class__.__name__} {e}")
            self._in_flight_prompt_ids.clear()
            await self._emit_status("error", reason="read_loop_error", detail=str(e))

    async def _record_wire_usage(self, token_usage: TokenUsage) -> None:
        """Record one StatusUpdate token_usage event as a UsageRecord.

        Only personal keys are metered here: team/shared traffic goes through
        the key proxy, which records usage itself (recording both would
        double-count).
        """
        info = self._key_info
        if info is None or info.source != "personal":
            return
        try:
            from cran_code.web.api_v2.keyproxy import record_usage

            await record_usage(
                user_id=info.owner_id,
                provider_key=info.provider_key,
                model=info.model,
                source=info.source,
                input_tokens=(
                    int(token_usage.input_other)
                    + int(token_usage.input_cache_read)
                    + int(token_usage.input_cache_creation)
                ),
                output_tokens=int(token_usage.output),
            )
        except Exception as e:
            logger.warning(f"Failed to meter wire usage: {e}")

    async def _handle_out_message(self, message: JSONRPCOutMessage) -> None:
        """Handle outbound message from worker."""
        match message:
            case JSONRPCSuccessResponse():
                was_busy = self.is_busy
                if message.id in self._in_flight_prompt_ids:
                    self._in_flight_prompt_ids.remove(message.id)
                if was_busy and not self.is_busy:
                    await self._emit_status("idle", reason="prompt_complete")
            case JSONRPCErrorResponse():
                was_busy = self.is_busy
                if message.id in self._in_flight_prompt_ids:
                    self._in_flight_prompt_ids.remove(message.id)
                if was_busy and not self.is_busy:
                    await self._emit_status("idle", reason="prompt_error")
            case _:
                return

    async def _encode_uploaded_files(self) -> AsyncGenerator[ContentPart]:
        """Encode uploaded files for sending to the model."""
        session = load_session_by_id(self.session_id)
        assert session is not None

        uploads_dir = session.cran_code_session.dir / "uploads"
        if not uploads_dir.exists():
            return

        # Load .sent marker left by fork to avoid re-sending inherited files.
        # The marker is kept (not deleted) so it survives process restarts.
        sent_marker = uploads_dir / ".sent"
        if sent_marker.exists():
            try:
                already_sent = json.loads(sent_marker.read_text(encoding="utf-8"))
                self._sent_files.update(already_sent)
            except Exception:
                pass

        all_files = sorted(
            (f for f in uploads_dir.iterdir() if f.name != ".sent"),
            key=lambda x: x.name,
        )
        files = [f for f in all_files if f.name not in self._sent_files]

        if not files:
            return

        # Build file list with paths and mime types
        file_infos: list[tuple[Path, str]] = []
        for file in files:
            mime_type, _ = mimetypes.guess_type(file.name)
            file_infos.append((file, mime_type or "application/octet-stream"))

        # Output file list summary
        file_list_lines = ["<uploaded_files>"]
        for idx, (file, _) in enumerate(file_infos, start=1):
            file_list_lines.append(f"{idx}. {file}")
        file_list_lines.append("</uploaded_files>")
        yield TextPart(text="\n".join(file_list_lines) + "\n\n")

        # Text file extensions
        text_extensions = {
            ".txt",
            ".md",
            ".json",
            ".yaml",
            ".yml",
            ".xml",
            ".html",
            ".css",
            ".js",
            ".ts",
            ".py",
            ".sh",
            ".csv",
            ".log",
            ".rst",
            ".toml",
            ".ini",
        }

        # Check model capabilities
        config = load_config()
        capabilities: set[ModelCapability] = set()
        if config.default_model:
            default = config.models.get(config.default_model)
            if default is not None:
                capabilities = default.capabilities or set()
        is_vision = "image_in" in capabilities
        is_video_in = "video_in" in capabilities

        # Process each file
        for file, mime_type in file_infos:
            file_path = str(file)
            ext = file.suffix.lower()

            if is_vision and mime_type.startswith("image/"):
                try:
                    content = file.read_bytes()
                    with Image.open(io.BytesIO(content)) as img:
                        pil_img: PILImage = img
                        width, height = pil_img.size
                        max_side = max(width, height)
                        # Downscale large images (API limit + prompt bloat) but
                        # preserve the source format: re-encoding a JPEG photo
                        # as PNG inflates it several-fold.
                        if max_side > 2000:
                            scale = 2000 / max_side
                            new_size = (int(width * scale), int(height * scale))
                            pil_img = pil_img.resize(  # pyright: ignore[reportUnknownMemberType]
                                new_size
                            )
                        save_format = "JPEG" if pil_img.format == "JPEG" else "PNG"
                        if save_format == "JPEG" and pil_img.mode not in ("RGB", "L"):
                            pil_img = pil_img.convert("RGB")
                        buffer = io.BytesIO()
                        if save_format == "JPEG":
                            pil_img.save(buffer, format="JPEG", quality=85)
                        else:
                            pil_img.save(buffer, format="PNG", optimize=True)
                        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
                        out_mime = (
                            "image/jpeg" if save_format == "JPEG" else "image/png"
                        )
                        tag = f'<image path="{file_path}" content_type="{out_mime}">'
                        yield TextPart(text=tag)
                        yield ImageURLPart(
                            image_url=ImageURLPart.ImageURL(url=f"data:{out_mime};base64,{encoded}")
                        )
                        yield TextPart(text="</image>\n\n")
                        self._sent_files.add(file.name)
                except Exception:
                    # Skip files that fail to encode - don't block the upload
                    pass
            elif is_video_in and mime_type.startswith("video/"):
                # For video files, emit a <video> tag for frontend display but don't embed content.
                # The agent will use ReadMediaFile tool to read it, which handles video uploads
                # properly.
                yield TextPart(text=f'<video path="{file_path}" content_type="{mime_type}">')
                yield TextPart(text="</video>\n\n")
                self._sent_files.add(file.name)
            elif ext in text_extensions or mime_type.startswith("text/"):
                try:
                    content = file.read_bytes()
                    text_content = content.decode("utf-8", errors="replace")
                    yield TextPart(text=f'<document path="{file_path}" content_type="{mime_type}">')
                    yield TextPart(text=text_content)
                    yield TextPart(text="</document>\n\n")
                    self._sent_files.add(file.name)
                except Exception:
                    # Skip files that fail to decode - don't block the upload
                    pass
        # Note: files that produced no parts are intentionally NOT marked as
        # sent so a failed upload is retried on the next prompt.

    async def _handle_in_message(self, message: JSONRPCInMessage) -> str | None:
        """Handle inbound message to worker, encoding uploaded files."""
        match message:
            case JSONRPCPromptMessage():
                user_input: list[ContentPart] = []
                async for part in self._encode_uploaded_files():
                    user_input.append(part)
                # Special marker for file-only uploads
                if isinstance(message.params.user_input, str):
                    if message.params.user_input != "KIMI_FILE_UPLOAD_WITHOUT_MESSAGE":
                        user_input.append(TextPart(text=message.params.user_input))
                else:
                    user_input += message.params.user_input
                return json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "method": "prompt",
                        "id": message.id,
                        "params": {
                            "user_input": [part.model_dump(mode="json") for part in user_input],
                        },
                    },
                    ensure_ascii=False,
                )
            case _:
                return None
        return None

    async def _broadcast(self, message: str) -> None:
        """Broadcast a message to all connected WebSockets."""
        disconnected: set[WebSocket] = set()

        async with self._ws_lock:
            websockets = list(self._websockets)
            to_send: list[WebSocket] = []
            for ws in websockets:
                buffer = self._replay_buffers.get(ws)
                if buffer is not None:
                    buffer.append(message)
                else:
                    to_send.append(ws)

        for ws in to_send:
            try:
                if ws.application_state == WebSocketState.CONNECTED:
                    await ws.send_text(message)
                else:
                    disconnected.add(ws)
            except Exception as e:
                logger.warning(f"websocket failed: {e.__class__.__name__} {e}")
                disconnected.add(ws)

        if disconnected:
            async with self._ws_lock:
                self._websockets -= disconnected
                self._websocket_count = len(self._websockets)
                for ws in disconnected:
                    self._replay_buffers.pop(ws, None)
            logger.debug(
                f"Broadcast: removed {len(disconnected)} disconnected ws, "
                f"remaining={self._websocket_count}"
            )

    async def add_websocket_and_begin_replay(self, ws: WebSocket) -> None:
        """Atomically attach a WebSocket and enter replay mode for it."""
        async with self._ws_lock:
            if ws not in self._websockets:
                self._websockets.add(ws)
                self._websocket_count = len(self._websockets)
            self._replay_buffers.setdefault(ws, [])
        logger.debug(f"WebSocket added (replay mode), count={self._websocket_count}")

    async def end_replay(self, ws: WebSocket) -> None:
        """Flush buffered live messages for a websocket after history replay."""
        while True:
            async with self._ws_lock:
                buffer = self._replay_buffers.get(ws)
                if buffer is None:
                    return
                if not buffer:
                    self._replay_buffers.pop(ws, None)
                    return
                chunk = buffer.copy()
                buffer.clear()

            if ws.application_state != WebSocketState.CONNECTED:
                logger.warning("end_replay: ws not connected, cleaning up replay buffer")
                async with self._ws_lock:
                    self._replay_buffers.pop(ws, None)
                return
            for message in chunk:
                try:
                    await ws.send_text(message)
                except Exception as e:
                    # Send failed — pop the replay buffer so _broadcast()
                    # sends directly (or detects disconnect) on the next call.
                    # Do NOT remove ws from _websockets here; let _broadcast()
                    # or session_stream's finally block handle cleanup.
                    logger.warning(f"end_replay: send_text failed during buffer flush: {e}")
                    async with self._ws_lock:
                        self._replay_buffers.pop(ws, None)
                    return

    async def _close_all_websockets(self) -> None:
        """Close all connected WebSockets."""
        async with self._ws_lock:
            websockets = list(self._websockets)
            self._websockets.clear()
            self._websocket_count = 0
            self._replay_buffers.clear()

        for ws in websockets:
            try:
                if ws.application_state == WebSocketState.CONNECTED:
                    await ws.close(code=1001, reason="Session process exited")
            except Exception:
                # Ignore errors closing already-disconnected WebSockets
                pass

    async def remove_websocket(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection from this session."""
        async with self._ws_lock:
            if ws in self._websockets:
                self._websockets.discard(ws)
                self._websocket_count = len(self._websockets)
                logger.debug(f"WebSocket removed, count={self._websocket_count}")
            self._replay_buffers.pop(ws, None)

    async def _prompt_gate_error(self) -> str | None:
        """Return an error message when the session owner cannot prompt now.

        Gates on key availability and shared-key quota so users get immediate,
        actionable feedback instead of an opaque provider failure deep inside
        the worker.
        """
        try:
            # Prefer the spawn-time snapshot when the worker is alive: it
            # reflects the model/provider the worker is actually using, which
            # may lag behind a freshly switched global default.
            info = self._key_info if self.is_alive and self._key_info else None
            if info is None:
                info = await self._resolve_session_key()
        except Exception as e:
            logger.warning(f"Prompt gate resolution failed: {e}")
            return None
        if info is None:
            return None  # legacy/local session: no gating
        if not info.api_key:
            if info.provider_type == "kimi" and not info.has_global_key:
                # Managed/OAuth kimi providers authenticate out of band.
                return None
            if info.has_global_key:
                return (
                    f"You do not have access to the shared key for provider "
                    f"'{info.provider_key}'. Ask an administrator for a grant, "
                    f"or configure your own key under Settings → Providers."
                )
            return (
                f"No API key configured for provider '{info.provider_key}'. "
                f"Add your own key under Settings → Providers, or ask an "
                f"administrator to share one."
            )
        if info.source == "shared":
            from cran_code.web.api_v2.keyproxy import _user_team_ids
            from cran_code.web.db.keys import remaining_quota

            team_ids = await _user_team_ids(info.owner_id)
            remaining = await remaining_quota(info.owner_id, info.provider_key, team_ids)
            if remaining is not None and remaining <= 0:
                return (
                    f"Your shared-key quota for provider '{info.provider_key}' is "
                    f"exhausted. Ask an administrator for more quota, or configure "
                    f"your own key under Settings → Providers."
                )
        return None

    async def send_message(self, message: str) -> None:
        """Send a message to the subprocess stdin.

        The session lock is held across (re)start and the stdin write so a
        concurrent ``restart_worker`` cannot terminate the process between
        the liveness check and the write.
        """
        # Validate before (re)start so that a fresh worker can replay the
        # client's cached initialize message.
        try:
            in_message = JSONRPCInMessageAdapter.validate_json(message)
        except ValueError as e:
            logger.error(f"{e.__class__.__name__} {e}: Invalid JSONRPC in message: {message}")
            return

        async with self._lock:
            if isinstance(in_message, JSONRPCInitializeMessage):
                # Cache the latest initialize so it survives worker restarts.
                self._cached_initialize_message = message

            if isinstance(in_message, JSONRPCPromptMessage):
                # Key/quota gate: answer immediately with an actionable error
                # instead of spawning a worker doomed to fail.
                gate_error = await self._prompt_gate_error()
                if gate_error is not None:
                    await self._broadcast(
                        JSONRPCErrorResponse(
                            id=in_message.id,
                            error=JSONRPCErrorObject(code=-2, message=gate_error),
                        ).model_dump_json()
                    )
                    return

            await self._start_locked()
            process = self._process
            assert process is not None
            assert process.stdin is not None

            if (
                isinstance(in_message, JSONRPCInitializeMessage)
                and self._worker_initialized
            ):
                # This worker generation already has its initialize (replayed
                # by start() or sent by another client); a duplicate would
                # confuse the wire server. The latest message is still cached
                # above for future restarts.
                return

            # Handle in message
            was_busy = self.is_busy
            if isinstance(in_message, JSONRPCPromptMessage):
                self._in_flight_prompt_ids.add(in_message.id)
                if not was_busy:
                    await self._emit_status("busy", reason="prompt")
            elif isinstance(in_message, JSONRPCCancelMessage) and not self.is_busy:
                # If not busy, return success to avoid errors
                await self._broadcast(
                    JSONRPCSuccessResponse(id=in_message.id, result={}).model_dump_json()
                )
                return

            new_message = await self._handle_in_message(in_message)
            if new_message is not None:
                message = new_message

            try:
                process.stdin.write((message + "\n").encode("utf-8"))
                await process.stdin.drain()
                if isinstance(in_message, JSONRPCInitializeMessage):
                    self._worker_initialized = True
            except (BrokenPipeError, ConnectionResetError) as e:
                # Worker died between the liveness check and the write.
                # Roll back bookkeeping and tell the client (with the
                # message's own id) so it can retry instead of hanging.
                logger.warning(f"Worker write failed, rolling back: {e}")
                if isinstance(in_message, JSONRPCPromptMessage):
                    self._in_flight_prompt_ids.discard(in_message.id)
                    if was_busy and not self.is_busy:
                        await self._emit_status("idle", reason="prompt_error")
                msg_id = getattr(in_message, "id", None) or str(uuid4())
                await self._broadcast(
                    JSONRPCErrorResponse(
                        id=msg_id,
                        error=JSONRPCErrorObject(
                            code=-1,
                            message="Session worker is unavailable; please retry.",
                        ),
                    ).model_dump_json()
                )
                return


class KimiCLIRunner:
    """Manages multiple session processes."""

    def __init__(self) -> None:
        """Initialize the runner."""
        self._sessions: dict[UUID, SessionProcess] = {}
        self._lock = asyncio.Lock()

    def start(self) -> None:
        """Start the runner (no-op, sessions started on demand)."""
        pass

    async def stop(self) -> None:
        """Stop all running sessions."""
        tasks: list[asyncio.Task[None]] = []
        for session in self._sessions.values():
            if session.is_running:
                tasks.append(asyncio.create_task(session.stop()))
        if tasks:
            _, pending = await asyncio.wait(tasks, timeout=5.0)
            for t in pending:
                t.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await t

    async def get_or_create_session(self, session_id: UUID) -> SessionProcess:
        """Get or create a session process."""
        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionProcess(session_id)
            return self._sessions[session_id]

    def get_session(self, session_id: UUID) -> SessionProcess | None:
        """Get a session process if it exists."""
        return self._sessions.get(session_id)

    async def detach_websocket(self, ws: WebSocket, session_id: UUID) -> None:
        """Detach a WebSocket from a session."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                await session.remove_websocket(ws)

    async def restart_running_workers(
        self,
        *,
        reason: str,
        force: bool,
    ) -> RestartWorkersSummary:
        """Restart all running workers to apply global config updates.

        Args:
            reason: Reason for the restart (e.g., "config_update")
            force: If True, also restart busy sessions (may interrupt prompts)

        Returns:
            Summary of restarted and skipped sessions
        """
        async with self._lock:
            running = [(sid, proc) for sid, proc in self._sessions.items() if proc.is_running]

        restarted: list[UUID] = []
        skipped_busy: list[UUID] = []

        # restart_worker performs the busy check under the session lock, so a
        # prompt cannot slip in between the check and the restart.
        results = await asyncio.gather(
            *(proc.restart_worker(reason=reason, force=force) for _, proc in running),
            return_exceptions=True,
        )
        for (session_id, _), result in zip(running, results, strict=True):
            if result is True:
                restarted.append(session_id)
            elif result is False:
                skipped_busy.append(session_id)
            else:
                logger.warning(f"Failed to restart worker for session {session_id}: {result}")

        return RestartWorkersSummary(
            restarted_session_ids=restarted,
            skipped_busy_session_ids=skipped_busy,
        )


@dataclass(slots=True)
class RestartWorkersSummary:
    """Summary of a restart_running_workers operation."""

    restarted_session_ids: list[UUID]
    skipped_busy_session_ids: list[UUID]
