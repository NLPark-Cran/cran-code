"""Tests for the v2 provider management API (cc-switch style presets + select)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from cran_code.config import Config, LLMModel, LLMProvider
from cran_code.web.api_v2 import providers as providers_api


@pytest.fixture
def fake_config(monkeypatch: pytest.MonkeyPatch) -> Config:
    config = Config()
    config.providers["kimi"] = LLMProvider(
        type="kimi",
        base_url="https://api.kimi.com/coding/v1",
        api_key=SecretStr("sk-kimi-test"),
    )
    config.models["kimi-for-coding"] = LLMModel(
        provider="kimi",
        model="kimi-for-coding",
        max_context_size=262144,
        capabilities={"thinking"},
        display_name="Kimi for Coding",
    )
    config.default_model = "kimi-for-coding"
    config.default_thinking = True

    saved: list[Config] = []
    monkeypatch.setattr(providers_api, "load_config", lambda: config)
    monkeypatch.setattr(providers_api, "save_config", lambda cfg: saved.append(cfg))
    config._test_saved = saved  # type: ignore[attr-defined]
    return config


def _upsert(**overrides: Any) -> providers_api.ProviderUpsertRequest:
    payload: dict[str, Any] = {
        "key": "tokendance",
        "type": "openai_legacy",
        "base_url": "https://tokendance.space/gateway/v1",
        "api_key": "sk-td-test",
        "models": None,
        "custom_headers": None,
        "reasoning_key": None,
    }
    payload.update(overrides)
    return providers_api.ProviderUpsertRequest(**payload)


class TestListProviders:
    @pytest.mark.asyncio
    async def test_lists_providers_without_leaking_keys(self, fake_config: Config):
        resp = await providers_api.list_providers(_=None)
        assert resp.default_model == "kimi-for-coding"
        assert len(resp.providers) == 1
        info = resp.providers[0]
        assert info.key == "kimi"
        assert info.has_api_key is True
        assert info.models[0].model == "kimi-for-coding"
        # No key material anywhere in the serialized response
        assert "sk-kimi-test" not in resp.model_dump_json()


class TestCreateProvider:
    @pytest.mark.asyncio
    async def test_create_with_explicit_models(self, fake_config: Config):
        req = _upsert(
            models=[
                providers_api.ProviderModelSpec(
                    model="kimi-k3",
                    max_context_size=1048576,
                    capabilities=["thinking", "image_in"],
                    display_name="Kimi K3",
                )
            ]
        )
        resp = await providers_api.create_provider(req, _=None)
        keys = {p.key for p in resp.providers}
        assert keys == {"kimi", "tokendance"}
        td = next(p for p in resp.providers if p.key == "tokendance")
        assert td.models[0].max_context_size == 1048576
        assert "kimi-k3" in td.model_keys
        assert fake_config.models["kimi-k3"].provider == "tokendance"
        assert len(fake_config._test_saved) == 1  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_create_conflict(self, fake_config: Config):
        with pytest.raises(HTTPException) as exc_info:
            await providers_api.create_provider(_upsert(key="kimi", models=[]), _=None)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_bad_key(self, fake_config: Config):
        with pytest.raises(HTTPException) as exc_info:
            await providers_api.create_provider(_upsert(key="bad key!", models=[]), _=None)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_create_auto_fetch(
        self, fake_config: Config, monkeypatch: pytest.MonkeyPatch
    ):
        async def fake_fetch(base_url: str, api_key: str):
            assert base_url == "https://tokendance.space/gateway/v1"
            assert api_key == "sk-td-test"
            return [
                providers_api.ProviderModelSpec(
                    model="kimi-k3", max_context_size=1048576, capabilities=["thinking"]
                )
            ]

        monkeypatch.setattr(providers_api, "_fetch_remote_models", fake_fetch)
        monkeypatch.setattr(providers_api, "_validate_fetch_url", AsyncMock())
        resp = await providers_api.create_provider(_upsert(), _=None)
        td = next(p for p in resp.providers if p.key == "tokendance")
        assert td.model_keys == ["kimi-k3"]


class TestUpdateProvider:
    @pytest.mark.asyncio
    async def test_update_keeps_stored_key_when_omitted(self, fake_config: Config):
        req = _upsert(key="kimi", api_key=None, base_url="https://api.kimi.com/coding/v2")
        await providers_api.update_provider("kimi", req, _=None)
        provider = fake_config.providers["kimi"]
        assert provider.base_url == "https://api.kimi.com/coding/v2"
        assert provider.api_key.get_secret_value() == "sk-kimi-test"

    @pytest.mark.asyncio
    async def test_update_replaces_models_and_repairs_default(self, fake_config: Config):
        req = _upsert(
            key="kimi",
            api_key=None,
            base_url="https://api.kimi.com/coding/v1",
            models=[
                providers_api.ProviderModelSpec(model="k3", max_context_size=262144),
            ],
        )
        resp = await providers_api.update_provider("kimi", req, _=None)
        # default model pointed at a removed model -> repaired to the first model
        assert resp.default_model == "k3"
        assert "kimi-for-coding" not in fake_config.models

    @pytest.mark.asyncio
    async def test_update_not_found(self, fake_config: Config):
        with pytest.raises(HTTPException) as exc_info:
            await providers_api.update_provider("nope", _upsert(key="nope"), _=None)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_key_mismatch_rejected(self, fake_config: Config):
        # L15: body key must match the path key
        with pytest.raises(HTTPException) as exc_info:
            await providers_api.update_provider("kimi", _upsert(key="other"), _=None)
        assert exc_info.value.status_code == 400


class TestSetModelContext:
    @pytest.mark.asyncio
    async def test_set_context_size(self, fake_config: Config):
        runner = AsyncMock()
        resp = await providers_api.set_model_context(
            "kimi-for-coding",
            providers_api.ModelContextRequest(max_context_size=1048576),
            _=None,
            runner=runner,
        )
        k3 = next(
            m for p in resp.providers for m, k in zip(p.models, p.model_keys, strict=True)
            if k == "kimi-for-coding"
        )
        assert k3.max_context_size == 1048576
        runner.restart_running_workers.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_context_not_found(self, fake_config: Config):
        with pytest.raises(HTTPException) as exc_info:
            await providers_api.set_model_context(
                "nope",
                providers_api.ModelContextRequest(max_context_size=1048576),
                _=None,
                runner=AsyncMock(),
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_set_context_with_restart(self, fake_config: Config):
        runner = AsyncMock()
        await providers_api.set_model_context(
            "kimi-for-coding",
            providers_api.ModelContextRequest(
                max_context_size=524288, restart_running_sessions=True
            ),
            _=None,
            runner=runner,
        )
        runner.restart_running_workers.assert_awaited_once()


class TestDeleteProvider:
    @pytest.mark.asyncio
    async def test_delete_blocked_for_default_provider(self, fake_config: Config):
        with pytest.raises(HTTPException) as exc_info:
            await providers_api.delete_provider("kimi", _=None)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_removes_provider_and_models(self, fake_config: Config):
        fake_config.providers["td"] = LLMProvider(
            type="openai_legacy",
            base_url="https://x.test/v1",
            api_key=SecretStr("k"),
        )
        fake_config.models["td-k3"] = LLMModel(
            provider="td", model="kimi-k3", max_context_size=1048576
        )
        resp = await providers_api.delete_provider("td", _=None)
        assert {p.key for p in resp.providers} == {"kimi"}
        assert "td-k3" not in fake_config.models

    @pytest.mark.asyncio
    async def test_delete_not_found(self, fake_config: Config):
        with pytest.raises(HTTPException) as exc_info:
            await providers_api.delete_provider("nope", _=None)
        assert exc_info.value.status_code == 404


class TestSelectModel:
    @pytest.mark.asyncio
    async def test_select_switches_default_and_restarts(self, fake_config: Config):
        fake_config.models["k3"] = LLMModel(
            provider="kimi", model="k3", max_context_size=262144
        )
        summary = SimpleNamespace(restarted_session_ids=["s1"], skipped_busy_session_ids=["s2"])
        calls: list[dict[str, Any]] = []

        class FakeRunner:
            async def restart_running_workers(self, *, reason: str, force: bool):
                calls.append({"reason": reason, "force": force})
                return summary

        req = providers_api.SelectModelRequest(default_model="k3", default_thinking=False)
        resp = await providers_api.select_model(req, _=None, runner=FakeRunner())
        assert resp.default_model == "k3"
        assert resp.default_thinking is False
        assert calls == [{"reason": "config_update", "force": False}]
        assert resp.restarted_session_ids == ["s1"]
        assert resp.skipped_busy_session_ids == ["s2"]

    @pytest.mark.asyncio
    async def test_select_rejects_unknown_model(self, fake_config: Config):
        class FakeRunner:
            async def restart_running_workers(self, *, reason: str, force: bool):  # pragma: no cover
                raise AssertionError("must not restart on validation failure")

        with pytest.raises(HTTPException) as exc_info:
            await providers_api.select_model(
                providers_api.SelectModelRequest(default_model="nope"),
                _=None,
                runner=FakeRunner(),
            )
        assert exc_info.value.status_code == 400


class TestHelpers:
    def test_model_key_dedup(self):
        existing: dict[str, LLMModel] = {"kimi-k3": LLMModel(provider="a", model="x", max_context_size=1)}
        assert providers_api._model_key("td", "kimi-k3", existing) == "td-kimi-k3"
        assert providers_api._model_key("td", "glm-5", existing) == "glm-5"

    def test_caps_from_payload_flags(self):
        caps = providers_api._caps_from_payload(
            {"supports_reasoning": True, "supports_image_in": True}, "some-model"
        )
        assert caps == ["image_in", "thinking"]

    def test_caps_from_payload_name_fallback(self):
        # k3 derives image/video input support from the LLM-side heuristics.
        caps = providers_api._caps_from_payload({}, "k3")
        assert caps == ["image_in", "thinking", "video_in"]
        assert providers_api._caps_from_payload({}, "plain-model") is None
