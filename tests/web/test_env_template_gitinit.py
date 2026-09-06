"""Tests for env-template injection and auto git init (base-layer features)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from kaos.path import KaosPath

from cran_code.session import Session
from cran_code.web.api.sessions import _auto_git_init, _maybe_inject_env_template
from cran_code.web.auth_v1 import CurrentUser


@pytest.fixture
def isolated_share_dir(monkeypatch, tmp_path: Path) -> Path:
    share_dir = tmp_path / "share"
    share_dir.mkdir()

    def _get_share_dir() -> Path:
        share_dir.mkdir(parents=True, exist_ok=True)
        return share_dir

    monkeypatch.setattr("cran_code.share.get_share_dir", _get_share_dir)
    monkeypatch.setattr("cran_code.metadata.get_share_dir", _get_share_dir)
    return share_dir


def _prompt_message(text: str, msg_id: str = "m1") -> str:
    return json.dumps(
        {"jsonrpc": "2.0", "id": msg_id, "method": "prompt", "params": {"user_input": text}}
    )


def _read_injected_text(message: str) -> str:
    ui = json.loads(message)["params"]["user_input"]
    assert isinstance(ui, list)
    return ui[0]["text"]


class TestEnvTemplateInjection:
    async def test_injects_on_first_prompt(
        self, isolated_share_dir: Path, tmp_path: Path, monkeypatch
    ) -> None:
        # Patch the session factory to return a fake template row

        class _FakeResult:
            def scalar_one_or_none(self):
                return "ENV: yolo, Debian 13"

        class _FakeSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def execute(self, _q):
                return _FakeResult()

        monkeypatch.setattr(
            "cran_code.web.db.AsyncSessionLocal", lambda: _FakeSession()
        )

        session = await Session.create(KaosPath.unsafe_from_local_path(tmp_path / "w"))
        (tmp_path / "w").mkdir(exist_ok=True)
        user = CurrentUser(id="u1", username="crina")

        out = await _maybe_inject_env_template(
            _prompt_message("hello"), session.dir, user
        )
        text = _read_injected_text(out)
        assert "<user-environment>" in text
        assert "yolo, Debian 13" in text

    async def test_skips_when_wire_not_empty(
        self, isolated_share_dir: Path, tmp_path: Path
    ) -> None:
        session = await Session.create(KaosPath.unsafe_from_local_path(tmp_path / "w"))
        (tmp_path / "w").mkdir(exist_ok=True)
        (session.dir / "wire.jsonl").write_text("{}\n", encoding="utf-8")
        user = CurrentUser(id="u1", username="crina")
        msg = _prompt_message("hello")
        assert await _maybe_inject_env_template(msg, session.dir, user) == msg

    async def test_skips_anonymous_and_upload_marker(
        self, isolated_share_dir: Path, tmp_path: Path
    ) -> None:
        session = await Session.create(KaosPath.unsafe_from_local_path(tmp_path / "w"))
        (tmp_path / "w").mkdir(exist_ok=True)
        anon = CurrentUser(id="v1_anonymous", username="anonymous")
        msg = _prompt_message("hello")
        assert await _maybe_inject_env_template(msg, session.dir, anon) == msg

        marker_msg = _prompt_message("KIMI_FILE_UPLOAD_WITHOUT_MESSAGE")
        user = CurrentUser(id="u1", username="crina")
        assert await _maybe_inject_env_template(marker_msg, session.dir, user) == marker_msg


class TestAutoGitInit:
    async def test_inits_normal_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "proj"
        target.mkdir()
        await _auto_git_init(target)
        assert (target / ".git").is_dir()

    async def test_skips_existing_repo_and_home(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / ".git").mkdir()
        await _auto_git_init(repo)  # no-op, must not raise
        await _auto_git_init(Path.home())  # no-op, must not raise
        # nonexistent dir: best-effort, no raise
        await _auto_git_init(tmp_path / "nope")
