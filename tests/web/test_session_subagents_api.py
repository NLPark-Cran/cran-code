"""Tests for the session subagents snapshot endpoint (swarm overview)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from kaos.path import KaosPath
from starlette.testclient import TestClient

from cran_code.session import Session
from cran_code.subagents import AgentLaunchSpec, SubagentStore
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


def _own_session(session: Session) -> None:
    """Mark the session as owned by the v1 anonymous test user."""
    from cran_code.session_state import load_session_state, save_session_state

    state = load_session_state(session.dir)
    state.owner_id = "v1_anonymous"
    save_session_state(state, session.dir)


def test_list_session_subagents(isolated_share_dir: Path, tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    session = asyncio.run(Session.create(KaosPath.unsafe_from_local_path(work)))
    _own_session(session)

    store = SubagentStore(session)
    store.create_instance(
        agent_id="a1234567",
        description="investigate parser bug",
        launch_spec=AgentLaunchSpec(
            agent_id="a1234567",
            subagent_type="explore",
            model_override=None,
            effective_model=None,
        ),
    )
    store.update_instance("a1234567", status="running_background", last_task_id="task-9")

    from cran_code.web.store.sessions import invalidate_sessions_cache

    invalidate_sessions_cache()

    with _make_client() as client:
        resp = client.get(f"/api/sessions/{session.id}/subagents")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    entry = data[0]
    assert entry["agent_id"] == "a1234567"
    assert entry["subagent_type"] == "explore"
    assert entry["description"] == "investigate parser bug"
    assert entry["status"] == "running_background"
    assert entry["last_task_id"] == "task-9"


def test_list_session_subagents_empty(isolated_share_dir: Path, tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    session = asyncio.run(Session.create(KaosPath.unsafe_from_local_path(work)))
    _own_session(session)

    from cran_code.web.store.sessions import invalidate_sessions_cache

    invalidate_sessions_cache()

    with _make_client() as client:
        resp = client.get(f"/api/sessions/{session.id}/subagents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_session_subagents_404(isolated_share_dir: Path) -> None:
    from cran_code.web.store.sessions import invalidate_sessions_cache

    invalidate_sessions_cache()

    with _make_client() as client:
        resp = client.get("/api/sessions/00000000-0000-0000-0000-000000000000/subagents")
    assert resp.status_code == 404
