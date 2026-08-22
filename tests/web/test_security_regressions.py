"""Regression tests for two kimi-code 0.25.0 vulnerability classes.

1. Percent-encoded / non-normalized paths must not bypass the v1 bearer-token
   middleware (upstream fixed `%2f`-style bypasses).
2. Symlinks inside a session work_dir must not allow reading files outside the
   work_dir via the session file API (upstream fixed fs symlink escape).
"""

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
    return TestClient(app)


def _get_raw(client: TestClient, raw_path: bytes):
    """GET with an exact raw path (httpx normalizes // and %2e in .get())."""
    import httpx

    req = client.build_request("GET", "http://testserver/")
    req.url = httpx.URL("http://testserver", raw_path=raw_path)
    return client.send(req)


class TestAuthPathNormalization:
    """Auth decisions must be made on the decoded, normalized path."""

    def test_percent_encoded_api_path_not_bypassed(self) -> None:
        with _make_client() as client:
            # %2F decodes to '/', so this is really /api/sessions/ — the
            # middleware must treat it as an API route (401), never serve data.
            resp = _get_raw(client, b"/api%2Fsessions/")
            assert resp.status_code in (401, 404, 405)
            assert b'"id"' not in resp.content

    def test_double_slash_api_path_not_bypassed(self) -> None:
        with _make_client() as client:
            resp = _get_raw(client, b"//api/sessions/")
            assert resp.status_code in (401, 404, 405)
            assert b'"id"' not in resp.content

    def test_encoded_dotdot_not_bypassed(self) -> None:
        with _make_client() as client:
            resp = _get_raw(client, b"/%2e%2e/api/sessions/")
            assert resp.status_code in (401, 404, 405)
            assert b'"id"' not in resp.content


class TestSessionFileSymlinkEscape:
    def _session(self, tmp_path: Path) -> Session:
        work = tmp_path / "work"
        work.mkdir(exist_ok=True)
        session = asyncio.run(Session.create(KaosPath.unsafe_from_local_path(work)))
        state = load_session_state(session.dir)
        state.owner_id = "v1_anonymous"
        save_session_state(state, session.dir)
        return session

    def test_symlink_escape_rejected(self, isolated_share_dir: Path, tmp_path: Path) -> None:
        session = self._session(tmp_path)
        outside = tmp_path / "outside.txt"
        outside.write_text("TOP SECRET", encoding="utf-8")
        # Plant a symlink inside the work dir pointing outside it
        link = tmp_path / "work" / "escape"
        link.symlink_to(outside)

        from cran_code.web.store.sessions import invalidate_sessions_cache

        invalidate_sessions_cache()

        client = _make_client()
        client.headers["Authorization"] = "Bearer test-token"
        with client:
            resp = client.get(f"/api/sessions/{session.id}/files/escape")
        assert resp.status_code in (400, 403, 404)
        assert b"TOP SECRET" not in resp.content

    def test_symlinked_dir_escape_rejected(
        self, isolated_share_dir: Path, tmp_path: Path
    ) -> None:
        session = self._session(tmp_path)
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        (outside_dir / "secret.txt").write_text("TOP SECRET", encoding="utf-8")
        link = tmp_path / "work" / "escape_dir"
        link.symlink_to(outside_dir, target_is_directory=True)

        from cran_code.web.store.sessions import invalidate_sessions_cache

        invalidate_sessions_cache()

        client = _make_client()
        client.headers["Authorization"] = "Bearer test-token"
        with client:
            resp = client.get(f"/api/sessions/{session.id}/files/escape_dir/secret.txt")
        assert resp.status_code in (400, 403, 404)
        assert b"TOP SECRET" not in resp.content

    def test_dotdot_traversal_rejected(self, isolated_share_dir: Path, tmp_path: Path) -> None:
        session = self._session(tmp_path)
        outside = tmp_path / "outside.txt"
        outside.write_text("TOP SECRET", encoding="utf-8")

        from cran_code.web.store.sessions import invalidate_sessions_cache

        invalidate_sessions_cache()

        client = _make_client()
        client.headers["Authorization"] = "Bearer test-token"
        with client:
            # Plain `..` segments (TestClient/httpx may normalize; the server
            # must still reject if they arrive raw).
            resp = client.get(f"/api/sessions/{session.id}/files/..%2Foutside.txt")
        assert resp.status_code in (400, 403, 404)
        assert b"TOP SECRET" not in resp.content
