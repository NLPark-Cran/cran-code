"""Tests for the v2 filesystem API sensitive-path guard and read size cap."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from cran_code.web.api_v2 import fs as fs_api


@pytest.mark.parametrize(
    "rel",
    [
        ".env",
        "sub/.env",
        ".git/config",
        "repo/.git/HEAD",
        ".ssh/id_rsa",
        "home/.aws/credentials",
        ".cran/server.env",
        "proj/.kimi/config.toml",
        ".config/config.toml",
        ".config/nested/server.env",
    ],
)
def test_is_sensitive_path_rejects(rel: str):
    assert fs_api._is_sensitive_path(Path(rel)) is True


@pytest.mark.parametrize(
    "rel",
    [
        "src/main.py",
        "README.md",
        "config.toml",
        "server.env",
        "src/config.toml",
        ".github/workflows/ci.yml",
        ".envrc",
    ],
)
def test_is_sensitive_path_allows(rel: str):
    assert fs_api._is_sensitive_path(Path(rel)) is False


@pytest.fixture
def fake_work_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    async def _resolve(project_id: str, user_id: str) -> Path:
        return tmp_path

    monkeypatch.setattr(fs_api, "_resolve_project_dir", _resolve)
    return tmp_path


@pytest.mark.asyncio
async def test_read_fs_rejects_sensitive_path(fake_work_dir: Path):
    (fake_work_dir / ".env").write_text("SECRET=1", encoding="utf-8")
    with pytest.raises(HTTPException) as exc_info:
        await fs_api.read_fs("proj-1", ".env", SimpleNamespace(id="user-1"))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_download_fs_rejects_sensitive_path(fake_work_dir: Path):
    cran_dir = fake_work_dir / ".cran"
    cran_dir.mkdir()
    (cran_dir / "server.env").write_text("SECRET=1", encoding="utf-8")
    with pytest.raises(HTTPException) as exc_info:
        await fs_api.download_fs("proj-1", ".cran/server.env", SimpleNamespace(id="user-1"))
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_read_fs_rejects_oversized_file(fake_work_dir: Path):
    big = fake_work_dir / "big.txt"
    big.write_bytes(b"x" * (fs_api._MAX_FILE_SIZE + 1))
    with pytest.raises(HTTPException) as exc_info:
        await fs_api.read_fs("proj-1", "big.txt", SimpleNamespace(id="user-1"))
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_read_fs_reads_normal_file(fake_work_dir: Path):
    (fake_work_dir / "hello.txt").write_text("hi", encoding="utf-8")
    resp = await fs_api.read_fs("proj-1", "hello.txt", SimpleNamespace(id="user-1"))
    assert isinstance(resp, fs_api.FsReadResponse)
    assert resp.content == "hi"
