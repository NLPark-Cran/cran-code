"""Tests for the session goal REST endpoints (goal mode P2)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from kaos.path import KaosPath
from starlette.testclient import TestClient

from cran_code.session import Session
from cran_code.session_state import load_session_state, save_session_state
from cran_code.web.app import create_app


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


def _make_client() -> TestClient:
    app = create_app(session_token="test-token")
    client = TestClient(app)
    client.headers["Authorization"] = "Bearer test-token"
    return client


def _new_session(tmp_path: Path) -> Session:
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    session = asyncio.run(Session.create(KaosPath.unsafe_from_local_path(work)))
    state = load_session_state(session.dir)
    state.owner_id = "v1_anonymous"
    save_session_state(state, session.dir)
    return session


@pytest.fixture
def session(isolated_share_dir: Path, tmp_path: Path) -> Session:
    s = _new_session(tmp_path)
    from cran_code.web.store.sessions import invalidate_sessions_cache

    invalidate_sessions_cache()
    return s


def test_goal_lifecycle_over_rest(session: Session) -> None:
    with _make_client() as client:
        base = f"/api/sessions/{session.id}/goal"

        # Initially no goal
        resp = client.get(base)
        assert resp.status_code == 200
        assert resp.json() == {"goal": None}

        # Create
        resp = client.post(base, json={"objective": "Fix all failing tests", "max_turns": 5})
        assert resp.status_code == 200
        goal = resp.json()["goal"]
        assert goal["status"] == "active"
        assert goal["objective"] == "Fix all failing tests"
        assert goal["budgets"]["max_turns"] == 5

        # Duplicate create → 409
        resp = client.post(base, json={"objective": "Another goal"})
        assert resp.status_code == 409

        # Pause → resume
        resp = client.post(f"{base}/pause")
        assert resp.status_code == 200
        assert resp.json()["goal"]["status"] == "paused"

        resp = client.post(f"{base}/resume")
        assert resp.status_code == 200
        assert resp.json()["goal"]["status"] == "active"

        # Cancel
        resp = client.delete(base)
        assert resp.status_code == 200
        assert resp.json() == {"goal": None}

        resp = client.get(base)
        assert resp.json() == {"goal": None}


def test_goal_endpoints_404_without_goal(session: Session) -> None:
    with _make_client() as client:
        base = f"/api/sessions/{session.id}/goal"
        assert client.post(f"{base}/pause").status_code == 404
        assert client.post(f"{base}/resume").status_code == 404
        assert client.delete(base).status_code == 404


def test_goal_create_validation(session: Session) -> None:
    with _make_client() as client:
        base = f"/api/sessions/{session.id}/goal"
        assert client.post(base, json={"objective": ""}).status_code == 422
        assert client.post(base, json={"objective": "x", "max_turns": 0}).status_code == 422
        assert client.post(base, json={"objective": "x", "max_seconds": 5}).status_code == 422


def test_goal_endpoints_404_unknown_session(isolated_share_dir: Path) -> None:
    with _make_client() as client:
        resp = client.get("/api/sessions/00000000-0000-0000-0000-000000000000/goal")
        assert resp.status_code == 404
