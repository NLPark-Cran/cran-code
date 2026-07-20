"""Tests for the v2 git API limit clamping."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from cran_code.web.api_v2 import git as git_api


@pytest.fixture
def fake_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    async def _require_project_dir(project_id: str, user_id: str) -> Path:
        return tmp_path

    calls: list[tuple[str, ...]] = []

    async def _run_git(cwd: Path, *args: str) -> tuple[int, str, str]:
        calls.append(args)
        return 0, "", ""

    monkeypatch.setattr(git_api, "_require_project_dir", _require_project_dir)
    monkeypatch.setattr(git_api, "_run_git", _run_git)
    return calls


@pytest.mark.asyncio
async def test_git_log_clamps_excessive_limit(fake_git: list[tuple[str, ...]]):
    await git_api.git_log("proj-1", limit=10**9, current_user=SimpleNamespace(id="user-1"))
    assert "--max-count=1000" in fake_git[0]


@pytest.mark.asyncio
async def test_git_log_keeps_reasonable_limit(fake_git: list[tuple[str, ...]]):
    await git_api.git_log("proj-1", limit=50, current_user=SimpleNamespace(id="user-1"))
    assert "--max-count=50" in fake_git[0]


@pytest.mark.asyncio
async def test_git_log_clamps_nonpositive_limit(fake_git: list[tuple[str, ...]]):
    await git_api.git_log("proj-1", limit=0, current_user=SimpleNamespace(id="user-1"))
    assert "--max-count=1" in fake_git[0]
