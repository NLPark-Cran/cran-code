"""Tests for the v1 global-config PATCH auth rules.

Public deployments (``restrict_sensitive_apis``) block anonymous and
v1-token callers, but a request carrying a valid v2 user JWT must be
allowed through so the web UI can switch models (including third-party
providers such as TokenDance).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from cran_code.config import Config, LLMModel, LLMProvider
from cran_code.web.api import config as config_api


@pytest.fixture
def fake_config(monkeypatch: pytest.MonkeyPatch) -> Config:
    config = Config()
    config.providers["kimi"] = LLMProvider(
        type="kimi", base_url="https://api.kimi.com", api_key=SecretStr("sk-test")
    )
    config.models["kimi-for-coding"] = LLMModel(
        provider="kimi", model="kimi-for-coding", max_context_size=262144
    )
    config.models["td-kimi-k3"] = LLMModel(
        provider="kimi", model="kimi-k3", max_context_size=1048576
    )
    config.default_model = "kimi-for-coding"
    monkeypatch.setattr(config_api, "load_config", lambda: config)
    monkeypatch.setattr(config_api, "save_config", lambda cfg: None)
    return config


class _FakeRunner:
    def __init__(self) -> None:
        self.restarts: list[dict[str, Any]] = []

    async def restart_running_workers(self, *, reason: str, force: bool):
        self.restarts.append({"reason": reason, "force": force})
        return SimpleNamespace(restarted_session_ids=[], skipped_busy_session_ids=[])


def _http_request(*, restricted: bool, auth_header: str | None = None):
    headers: dict[str, str] = {}
    if auth_header is not None:
        headers["authorization"] = auth_header
    return SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(restrict_sensitive_apis=restricted)
        ),
        headers=headers,
    )


def _patch_request(model: str) -> config_api.UpdateGlobalConfigRequest:
    return config_api.UpdateGlobalConfigRequest(default_model=model)


@pytest.mark.asyncio
async def test_patch_blocked_for_anonymous_when_restricted(fake_config: Config):
    with pytest.raises(HTTPException) as exc_info:
        await config_api.update_global_config(
            _patch_request("td-kimi-k3"),
            _http_request(restricted=True),
            runner=_FakeRunner(),
        )
    assert exc_info.value.status_code == 403
    assert fake_config.default_model == "kimi-for-coding"


@pytest.mark.asyncio
async def test_patch_allowed_for_v2_user_when_restricted(
    fake_config: Config, monkeypatch: pytest.MonkeyPatch
):
    async def fake_get_current_user(token: str):
        return SimpleNamespace(id="user-1", is_active=True)

    monkeypatch.setattr(
        "cran_code.web.auth_v2.jwt.get_current_user", fake_get_current_user
    )

    runner = _FakeRunner()
    resp = await config_api.update_global_config(
        _patch_request("td-kimi-k3"),
        _http_request(restricted=True, auth_header="Bearer valid.jwt.token"),
        runner=runner,
    )
    assert fake_config.default_model == "td-kimi-k3"
    assert resp.config.default_model == "td-kimi-k3"
    assert runner.restarts == [{"reason": "config_update", "force": False}]


@pytest.mark.asyncio
async def test_patch_blocked_for_invalid_v2_token_when_restricted(
    fake_config: Config, monkeypatch: pytest.MonkeyPatch
):
    async def fake_get_current_user(token: str):
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    monkeypatch.setattr(
        "cran_code.web.auth_v2.jwt.get_current_user", fake_get_current_user
    )

    with pytest.raises(HTTPException) as exc_info:
        await config_api.update_global_config(
            _patch_request("td-kimi-k3"),
            _http_request(restricted=True, auth_header="Bearer bad.token"),
            runner=_FakeRunner(),
        )
    assert exc_info.value.status_code == 403
    assert fake_config.default_model == "kimi-for-coding"


@pytest.mark.asyncio
async def test_patch_allowed_for_anyone_when_unrestricted(fake_config: Config):
    resp = await config_api.update_global_config(
        _patch_request("td-kimi-k3"),
        _http_request(restricted=False),
        runner=_FakeRunner(),
    )
    assert resp.config.default_model == "td-kimi-k3"


@pytest.mark.asyncio
async def test_toml_endpoints_stay_blocked_for_v2_users(
    fake_config: Config, monkeypatch: pytest.MonkeyPatch
):
    """Raw config.toml access must remain restricted for non-admin v2 users."""

    async def fake_get_current_user(token: str):
        return SimpleNamespace(id="user-1", is_active=True)

    monkeypatch.setattr(
        "cran_code.web.auth_v2.jwt.get_current_user", fake_get_current_user
    )
    req = _http_request(restricted=True, auth_header="Bearer valid.jwt.token")

    with pytest.raises(HTTPException) as exc_info:
        await config_api.get_config_toml(req)
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        await config_api.update_config_toml(
            config_api.UpdateConfigTomlRequest(content=""), req
        )
    assert exc_info.value.status_code == 403


_VALID_TOML = """\
default_model = "kimi-for-coding"

[providers.kimi]
type = "kimi"
base_url = "https://api.kimi.com"
api_key = "sk-secret"

[models.kimi-for-coding]
provider = "kimi"
model = "kimi-for-coding"
max_context_size = 262144
"""


@pytest.fixture
def fake_config_file(tmp_path, monkeypatch: pytest.MonkeyPatch):
    config_file = tmp_path / "config.toml"
    config_file.write_text(_VALID_TOML, encoding="utf-8")
    monkeypatch.setattr(config_api, "get_config_file", lambda: config_file)
    return config_file


@pytest.mark.asyncio
async def test_get_toml_redacts_provider_api_keys(fake_config_file):
    resp = await config_api.get_config_toml(_http_request(restricted=False))
    assert resp.redacted is True
    assert "sk-secret" not in resp.content
    assert 'api_key = "***redacted***"' in resp.content
    # Non-provider content is preserved.
    assert 'default_model = "kimi-for-coding"' in resp.content


@pytest.mark.asyncio
async def test_toml_endpoints_allowed_for_v2_admin_when_restricted(
    fake_config_file, monkeypatch: pytest.MonkeyPatch
):
    from cran_code.web.db.models import UserRole

    async def fake_get_current_user(token: str):
        return SimpleNamespace(id="admin-1", is_active=True, role=UserRole.admin)

    monkeypatch.setattr(
        "cran_code.web.auth_v2.jwt.get_current_user", fake_get_current_user
    )
    req = _http_request(restricted=True, auth_header="Bearer admin.jwt.token")

    resp = await config_api.get_config_toml(req)
    assert resp.redacted is True

    runner = _FakeRunner()
    put_resp = await config_api.update_config_toml(
        config_api.UpdateConfigTomlRequest(content=_VALID_TOML), req, runner=runner
    )
    assert put_resp.success is True
    assert runner.restarts == [{"reason": "config_update", "force": False}]


@pytest.mark.asyncio
async def test_update_toml_restarts_running_workers(fake_config_file):
    runner = _FakeRunner()
    resp = await config_api.update_config_toml(
        config_api.UpdateConfigTomlRequest(content=_VALID_TOML),
        _http_request(restricted=False),
        runner=runner,
    )
    assert resp.success is True
    assert resp.error is None
    assert runner.restarts == [{"reason": "config_update", "force": False}]


@pytest.mark.asyncio
async def test_update_toml_invalid_content_does_not_restart(fake_config_file):
    runner = _FakeRunner()
    resp = await config_api.update_config_toml(
        config_api.UpdateConfigTomlRequest(content="not [valid toml"),
        _http_request(restricted=False),
        runner=runner,
    )
    assert resp.success is False
    assert resp.error is not None
    assert runner.restarts == []
