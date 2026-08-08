"""Tests for initialize-message replay across worker restarts.

Worker restarts (e.g. ``restart_running_workers`` after a config/model change)
keep client WebSockets alive, so the browser never re-sends its ``initialize``
message. SessionProcess must cache the latest initialize and replay it to every
freshly spawned worker so the new wire server restores client capabilities
(``supports_question`` / ``supports_plan_mode``). Without the replay,
AskUserQuestion stays visible but unsupported, and models that call it (e.g. K3)
hit ``QuestionNotSupported``.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from cran_code.web.runner.process import SessionProcess
from cran_code.wire.jsonrpc import JSONRPCSuccessResponse


def _patch_session_dir(tmp_path: Path):
    """Make load_session_by_id return a session pointing at an empty tmp dir.

    The session is a legacy (ownerless) one so the key-resolution gate in
    send_message / _build_worker_env skips DB lookups entirely.
    """
    session = MagicMock()
    session.cran_code_session.dir = tmp_path
    session.cran_code_session.state.owner_id = None
    return patch(
        "cran_code.web.runner.process.load_session_by_id", return_value=session
    )


class _FakeStdin:
    def __init__(self) -> None:
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    async def drain(self) -> None:
        pass


class _FakeWorkerProcess:
    """Minimal stand-in for asyncio.subprocess.Process."""

    def __init__(self) -> None:
        self.stdin = _FakeStdin()
        self.stdout = asyncio.StreamReader()
        self.stdout.feed_eof()
        self.stderr = asyncio.StreamReader()
        self.stderr.feed_eof()
        self.returncode: int | None = None

    def terminate(self) -> None:
        self.returncode = -15

    def kill(self) -> None:
        self.returncode = -9

    async def wait(self) -> int:
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


def _initialize_message(msg_id: str = "init-1") -> str:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": msg_id,
            "params": {
                "protocol_version": "1.0",
                "client": {"name": "kiwi", "version": "1.49.0"},
                "capabilities": {
                    "supports_question": True,
                    "supports_plan_mode": True,
                },
            },
        }
    )


def _prompt_message(msg_id: str = "prompt-1") -> str:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "prompt",
            "id": msg_id,
            "params": {"user_input": "hello"},
        }
    )


class _FakeProcessFactory:
    """Creates a new fake worker per spawn and records them in order."""

    def __init__(self) -> None:
        self.processes: list[_FakeWorkerProcess] = []

    def __call__(self, *args: object, **kwargs: object) -> _FakeWorkerProcess:
        proc = _FakeWorkerProcess()
        self.processes.append(proc)
        return proc


@pytest.mark.asyncio
async def test_initialize_written_once_on_first_start(tmp_path: Path) -> None:
    """The initialize that triggers the spawn must reach the worker exactly once."""
    factory = _FakeProcessFactory()
    sp = SessionProcess(uuid4())

    with (
        patch("asyncio.create_subprocess_exec", side_effect=factory),
        _patch_session_dir(tmp_path),
    ):
        init_msg = _initialize_message()
        await sp.send_message(init_msg)

        assert len(factory.processes) == 1
        worker = factory.processes[0]
        assert worker.stdin.writes == [(init_msg + "\n").encode()]

        # A subsequent prompt is forwarded normally.
        await sp.send_message(_prompt_message())
        assert len(worker.stdin.writes) == 2
        assert b'"method": "prompt"' in worker.stdin.writes[1]


@pytest.mark.asyncio
async def test_initialize_replayed_after_worker_restart() -> None:
    """A restarted worker must receive the cached initialize (capabilities)."""
    factory = _FakeProcessFactory()
    sp = SessionProcess(uuid4())

    with patch("asyncio.create_subprocess_exec", side_effect=factory):
        init_msg = _initialize_message()
        await sp.send_message(init_msg)
        assert len(factory.processes) == 1

        await sp.restart_worker(reason="config_update")

        assert len(factory.processes) == 2
        new_worker = factory.processes[1]
        # The fresh worker gets the cached initialize without any client resend.
        assert new_worker.stdin.writes == [(init_msg + "\n").encode()]


@pytest.mark.asyncio
async def test_restart_without_initialize_replays_nothing(tmp_path: Path) -> None:
    """If no client ever initialized, a restart must not write anything."""
    factory = _FakeProcessFactory()
    sp = SessionProcess(uuid4())

    with (
        patch("asyncio.create_subprocess_exec", side_effect=factory),
        _patch_session_dir(tmp_path),
    ):
        await sp.send_message(_prompt_message())
        assert len(factory.processes) == 1

        # The prompt above marks the session busy; force the restart.
        restarted = await sp.restart_worker(reason="config_update", force=True)
        assert restarted is True

        assert len(factory.processes) == 2
        assert factory.processes[1].stdin.writes == []


@pytest.mark.asyncio
async def test_restart_skipped_when_busy_unless_forced(tmp_path: Path) -> None:
    """A busy session is not restarted unless force=True (checked under lock)."""
    factory = _FakeProcessFactory()
    sp = SessionProcess(uuid4())

    with (
        patch("asyncio.create_subprocess_exec", side_effect=factory),
        _patch_session_dir(tmp_path),
    ):
        await sp.send_message(_prompt_message())
        assert sp.is_busy is True

        skipped = await sp.restart_worker(reason="config_update")
        assert skipped is False
        assert len(factory.processes) == 1  # still the original worker

        forced = await sp.restart_worker(reason="config_update", force=True)
        assert forced is True
        assert len(factory.processes) == 2
        assert sp.is_busy is False  # in-flight ids cleared by restart


@pytest.mark.asyncio
async def test_new_client_initialize_after_restart_not_skipped() -> None:
    """A duplicate initialize for the same worker generation is deduped, but
    the latest initialize is still cached and replayed on the NEXT restart."""
    factory = _FakeProcessFactory()
    sp = SessionProcess(uuid4())

    with patch("asyncio.create_subprocess_exec", side_effect=factory):
        await sp.send_message(_initialize_message("init-1"))
        await sp.restart_worker(reason="config_update")
        new_worker = factory.processes[1]
        assert len(new_worker.stdin.writes) == 1  # replay only

        # A new client connects and sends its own initialize: cached, but NOT
        # forwarded — this worker generation already has one.
        new_init = _initialize_message("init-2")
        await sp.send_message(new_init)
        assert len(new_worker.stdin.writes) == 1

        # On the next restart the LATEST initialize (init-2) is replayed.
        await sp.restart_worker(reason="config_update")
        third_worker = factory.processes[2]
        assert third_worker.stdin.writes == [(new_init + "\n").encode()]


@pytest.mark.asyncio
async def test_deduped_initialize_gets_cached_result() -> None:
    """Slash commands must survive initialize dedup: the second client's
    initialize is answered from the cached worker result, not dropped."""
    factory = _FakeProcessFactory()
    sp = SessionProcess(uuid4())
    broadcasts: list[str] = []

    async def fake_broadcast(msg: str) -> None:
        broadcasts.append(msg)

    sp._broadcast = fake_broadcast  # type: ignore[method-assign]

    with patch("asyncio.create_subprocess_exec", side_effect=factory):
        await sp.send_message(_initialize_message("init-1"))
        worker = factory.processes[0]
        assert worker.stdin.writes == [(_initialize_message("init-1") + "\n").encode()]

        # Worker answers the initialize with a slash-command list.
        await sp._handle_out_message(
            JSONRPCSuccessResponse(
                id="init-1", result={"slash_commands": ["/compact", "/clear"]}
            )
        )

        # Second client's initialize is deduped but answered from cache.
        await sp.send_message(_initialize_message("init-2"))
        assert len(worker.stdin.writes) == 1  # not forwarded
        assert broadcasts, "cached initialize result should be broadcast"
        response = json.loads(broadcasts[-1])
        assert response["id"] == "init-2"
        assert response["result"]["slash_commands"] == ["/compact", "/clear"]
