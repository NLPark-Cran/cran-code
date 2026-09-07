"""Tests for cran_code.utils.oom_score."""

from __future__ import annotations

import os

import pytest

from cran_code.utils.oom_score import (
    OOM_SCORE_BACKGROUND_WORKER,
    OOM_SCORE_SERVER,
    OOM_SCORE_SESSION_WORKER,
    set_oom_score_adj,
)


def test_score_ordering() -> None:
    """Background workers must be killed before session workers, which must be
    killed before the server."""
    assert OOM_SCORE_BACKGROUND_WORKER > 0
    assert OOM_SCORE_SESSION_WORKER < 0
    assert OOM_SCORE_SERVER < OOM_SCORE_SESSION_WORKER


def test_write_and_clamp(tmp_path) -> None:
    proc = tmp_path / "oom_score_adj"
    proc.write_text("0")

    assert set_oom_score_adj(500, _path=str(proc)) is True
    assert proc.read_text() == "500"

    assert set_oom_score_adj(-800, _path=str(proc)) is True
    assert proc.read_text() == "-800"

    # Values are clamped to the kernel range.
    assert set_oom_score_adj(5000, _path=str(proc)) is True
    assert proc.read_text() == "1000"
    assert set_oom_score_adj(-5000, _path=str(proc)) is True
    assert proc.read_text() == "-1000"


def test_missing_path_returns_false(tmp_path) -> None:
    missing = tmp_path / "does-not-exist"
    assert set_oom_score_adj(100, _path=str(missing)) is False


def test_non_posix_noop(monkeypatch, tmp_path) -> None:
    proc = tmp_path / "oom_score_adj"
    proc.write_text("0")
    monkeypatch.setattr(os, "name", "nt")
    assert set_oom_score_adj(100, _path=str(proc)) is False
    assert proc.read_text() == "0"


@pytest.mark.skipif(os.name != "posix", reason="POSIX only")
def test_real_proc_path_never_raises() -> None:
    """Calling with the real /proc path must never raise, regardless of
    permissions (CI may run unprivileged)."""
    set_oom_score_adj(0)  # result depends on environment; must not raise
