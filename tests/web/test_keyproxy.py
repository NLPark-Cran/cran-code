"""Tests for the provider key proxy and worker-env key injection.

Covers:
- proxy token mint/verify (roundtrip, tamper, wrong secret)
- SessionProcess._build_worker_env injection rules (personal direct,
  team/shared via proxy, kimi personal via CRAN_API_KEY)
- the prompt gate (no key / no grant / quota exhausted -> JSONRPC error,
  no worker spawn)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from cran_code.web.api_v2.keyproxy import mint_proxy_token, verify_proxy_token
from cran_code.web.runner.process import _SessionKeyInfo, SessionProcess


class TestProxyToken:
    def test_roundtrip(self) -> None:
        token = mint_proxy_token("user-1", "tokendance", "team")
        claims = verify_proxy_token(token)
        assert claims == {"u": "user-1", "p": "tokendance", "s": "team"}

    def test_tampered_payload_rejected(self) -> None:
        token = mint_proxy_token("user-1", "tokendance", "team")
        body = token[len("cwk_") :]
        payload, _, sig = body.partition(".")
        other = mint_proxy_token("user-2", "tokendance", "team")[len("cwk_") :]
        other_payload = other.partition(".")[0]
        assert verify_proxy_token(f"cwk_{other_payload}.{sig}") is None

    def test_garbage_rejected(self) -> None:
        assert verify_proxy_token("cwk_nonsense") is None
        assert verify_proxy_token("sk-whatever") is None
        assert verify_proxy_token("") is None

    def test_wrong_secret_rejected(self) -> None:
        token = mint_proxy_token("user-1", "tokendance", "shared")
        with patch.dict(os.environ, {"CRAN_JWT_SECRET": "another-secret"}):
            assert verify_proxy_token(token) is None


def _info(**overrides: object) -> _SessionKeyInfo:
    base = {
        "owner_id": "user-1",
        "provider_key": "tokendance",
        "provider_type": "openai_legacy",
        "model": "k3",
        "has_global_key": True,
        "api_key": "sk-real",
        "source": "personal",
    }
    base.update(overrides)
    return _SessionKeyInfo(**base)  # type: ignore[arg-type]


class TestBuildWorkerEnv:
    async def _env(self, sp: SessionProcess, info: _SessionKeyInfo | None) -> dict[str, str]:
        with (
            patch(
                "cran_code.web.runner.process.get_clean_env",
                return_value={"CRAN_JWT_SECRET": "x", "PATH": "/bin"},
            ),
            patch.object(SessionProcess, "_resolve_session_key", return_value=info),
        ):
            return await sp._build_worker_env()

    @pytest.mark.asyncio
    async def test_personal_openai_key_injected_directly(self) -> None:
        sp = SessionProcess(uuid4())
        env = await self._env(sp, _info())
        assert env["OPENAI_API_KEY"] == "sk-real"
        assert "OPENAI_BASE_URL" not in env
        # Sanitization still applies
        assert "CRAN_JWT_SECRET" not in env
        assert env["PATH"] == "/bin"

    @pytest.mark.asyncio
    async def test_team_key_routed_via_proxy(self) -> None:
        sp = SessionProcess(uuid4())
        with patch.dict(os.environ, {"CRAN_KEY_PROXY_PORT": "5496"}):
            env = await self._env(sp, _info(source="team", api_key="sk-team"))
        assert env["OPENAI_BASE_URL"] == "http://127.0.0.1:5496/px/v1"
        token = env["OPENAI_API_KEY"]
        claims = verify_proxy_token(token)
        assert claims == {"u": "user-1", "p": "tokendance", "s": "team"}
        assert "sk-team" not in json.dumps(env)

    @pytest.mark.asyncio
    async def test_shared_key_routed_via_proxy(self) -> None:
        sp = SessionProcess(uuid4())
        with patch.dict(os.environ, {"CRAN_KEY_PROXY_PORT": "5496"}):
            env = await self._env(sp, _info(source="shared", api_key="sk-shared"))
        assert env["OPENAI_BASE_URL"].endswith("/px/v1")
        assert "sk-shared" not in json.dumps(env)

    @pytest.mark.asyncio
    async def test_kimi_personal_key_uses_cran_api_key(self) -> None:
        sp = SessionProcess(uuid4())
        env = await self._env(sp, _info(provider_type="kimi", api_key="sk-kimi"))
        assert env["CRAN_API_KEY"] == "sk-kimi"
        assert "OPENAI_API_KEY" not in env

    @pytest.mark.asyncio
    async def test_kimi_shared_key_not_injected(self) -> None:
        # Shared kimi stays on the config.toml / OAuth flow.
        sp = SessionProcess(uuid4())
        env = await self._env(sp, _info(provider_type="kimi", source="shared"))
        assert "CRAN_API_KEY" not in env
        assert "OPENAI_BASE_URL" not in env

    @pytest.mark.asyncio
    async def test_no_resolution_no_injection(self) -> None:
        sp = SessionProcess(uuid4())
        env = await self._env(sp, None)
        assert "OPENAI_API_KEY" not in env
        assert "CRAN_API_KEY" not in env

    @pytest.mark.asyncio
    async def test_unresolved_key_no_injection(self) -> None:
        sp = SessionProcess(uuid4())
        env = await self._env(sp, _info(api_key="", source=""))
        assert "OPENAI_API_KEY" not in env


class TestPromptGate:
    def _session_patch(self, tmp_path: Path):
        session = MagicMock()
        session.cran_code_session.dir = tmp_path
        session.cran_code_session.state.owner_id = "user-1"
        return patch(
            "cran_code.web.runner.process.load_session_by_id", return_value=session
        )

    def _prompt(self, msg_id: str = "p-1") -> str:
        return json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "prompt",
                "id": msg_id,
                "params": {"user_input": "hi"},
            }
        )

    @pytest.mark.asyncio
    async def test_gate_blocks_prompt_without_key(self, tmp_path: Path) -> None:
        sp = SessionProcess(uuid4())
        sp._broadcast = AsyncMock()  # type: ignore[method-assign]
        info = _info(api_key="", source="", has_global_key=False)
        with (
            self._session_patch(tmp_path),
            patch.object(SessionProcess, "_resolve_session_key", return_value=info),
            patch("asyncio.create_subprocess_exec") as spawn,
        ):
            await sp.send_message(self._prompt())
        spawn.assert_not_called()
        payload = json.loads(sp._broadcast.await_args.args[0])  # type: ignore[attr-defined]
        assert payload["id"] == "p-1"
        assert "No API key configured" in payload["error"]["message"]

    @pytest.mark.asyncio
    async def test_gate_blocks_shared_without_grant(self, tmp_path: Path) -> None:
        sp = SessionProcess(uuid4())
        sp._broadcast = AsyncMock()  # type: ignore[method-assign]
        info = _info(api_key="", source="", has_global_key=True)
        with (
            self._session_patch(tmp_path),
            patch.object(SessionProcess, "_resolve_session_key", return_value=info),
            patch("asyncio.create_subprocess_exec") as spawn,
        ):
            await sp.send_message(self._prompt())
        spawn.assert_not_called()
        payload = json.loads(sp._broadcast.await_args.args[0])  # type: ignore[attr-defined]
        assert "do not have access" in payload["error"]["message"]

    @pytest.mark.asyncio
    async def test_gate_blocks_exhausted_quota(self, tmp_path: Path) -> None:
        sp = SessionProcess(uuid4())
        sp._broadcast = AsyncMock()  # type: ignore[method-assign]
        info = _info(source="shared")
        with (
            self._session_patch(tmp_path),
            patch.object(SessionProcess, "_resolve_session_key", return_value=info),
            patch(
                "cran_code.web.db.keys.remaining_quota",
                new=AsyncMock(return_value=0),
            ),
            patch(
                "cran_code.web.api_v2.keyproxy._user_team_ids",
                new=AsyncMock(return_value=[]),
            ),
            patch("asyncio.create_subprocess_exec") as spawn,
        ):
            await sp.send_message(self._prompt())
        spawn.assert_not_called()
        payload = json.loads(sp._broadcast.await_args.args[0])  # type: ignore[attr-defined]
        assert "quota" in payload["error"]["message"].lower()
