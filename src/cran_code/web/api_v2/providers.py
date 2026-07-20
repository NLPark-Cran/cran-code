"""Provider management API (v2).

Inspired by cc-switch's provider-preset model: users manage a list of
providers (base URL + API key + models) stored in the shared config.toml,
and switch the active model globally (running workers are restarted, which
is the fix for cc-switch issue #3057 — stale provider in live sessions).

Security notes:
- API keys are write-only: responses never include key material, only
  ``has_api_key``.
- Endpoints require a valid v2 JWT (any authenticated user). Providers are
  global/shared on this deployment, so changes affect all users.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from typing import Any, Literal, cast
from urllib.parse import urlparse

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, SecretStr

from cran_code.config import LLMModel, LLMProvider, load_config, save_config
from cran_code.llm import ModelCapability, derive_model_capabilities
from cran_code.web.auth_v2.jwt import User as JWTUser, require_admin, require_user
from cran_code.web.runner.process import KimiCLIRunner

router = APIRouter(prefix="/api/v2/providers", tags=["providers"])

_PROVIDER_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_MODEL_KEY_RE = re.compile(r"[^A-Za-z0-9_-]+")

# Serializes load-modify-save cycles on the shared config.toml (shared with
# the v1 config routes via cran_code.config.config_write_lock).
from cran_code.config import config_write_lock as _config_lock


def _normalize_base_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def _is_loopback_host(hostname: str) -> bool:
    if hostname in {"localhost", "localhost.localdomain"}:
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


async def _validate_fetch_url(base_url: str) -> None:
    """SSRF guard for server-side probes of ``{base_url}/models`` (C1).

    Rules: https only (http allowed for loopback), and the hostname must not
    resolve to a private/loopback/link-local/reserved address.
    """
    parsed = urlparse(base_url if "://" in base_url else f"https://{base_url}")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid base_url"
        )
    loopback = _is_loopback_host(hostname)
    if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="base_url must use https (http is only allowed for localhost)",
        )
    if loopback:
        return

    def _resolve() -> list[str]:
        try:
            infos = socket.getaddrinfo(hostname, None)
        except OSError:
            return []
        return [str(info[4][0]) for info in infos]

    addresses = await asyncio.to_thread(_resolve)
    if not addresses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not resolve host '{hostname}'",
        )
    for addr in addresses:
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="base_url must not point to a private or internal address",
            )

ProviderTypeStr = Literal[
    "kimi",
    "openai_legacy",
    "openai_responses",
    "anthropic",
    "google_genai",
    "gemini",
    "vertexai",
]


class ProviderModelSpec(BaseModel):
    """A model served by a provider."""

    model: str
    max_context_size: int = 262144
    capabilities: list[str] | None = None
    display_name: str | None = None


class ProviderInfo(BaseModel):
    key: str
    type: str
    base_url: str
    has_api_key: bool
    models: list[ProviderModelSpec]
    model_keys: list[str]


class ProviderListResponse(BaseModel):
    default_model: str
    default_thinking: bool
    providers: list[ProviderInfo]


class ProviderUpsertRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=64)
    type: ProviderTypeStr
    base_url: str = Field(..., min_length=1)
    api_key: str | None = None
    """New API key. ``None`` on update keeps the stored key."""
    models: list[ProviderModelSpec] | None = None
    """Explicit model list. When ``None`` on create, models are fetched from
    ``{base_url}/models``; on update the existing list is kept."""
    custom_headers: dict[str, str] | None = None
    reasoning_key: str | None = None


class FetchModelsRequest(BaseModel):
    type: ProviderTypeStr = "openai_legacy"
    base_url: str
    api_key: str | None = None
    provider_key: str | None = None
    """Reuse the stored key of this provider when ``api_key`` is omitted."""


class FetchModelsResponse(BaseModel):
    models: list[ProviderModelSpec]


class SelectModelRequest(BaseModel):
    default_model: str
    default_thinking: bool | None = None
    restart_running_sessions: bool = True
    force_restart_busy_sessions: bool = False


class SelectModelResponse(BaseModel):
    default_model: str
    default_thinking: bool
    restarted_session_ids: list[str] | None = None
    skipped_busy_session_ids: list[str] | None = None


class ModelContextRequest(BaseModel):
    """Set a model's context window size.

    K3 example: 262144 (Moderato) / 524288 / 1048576 (Allegretto+ 1M). The
    usable ceiling depends on the subscription tier of the account behind the
    provider key.
    """

    max_context_size: int = Field(..., ge=1024, le=10_000_000)
    restart_running_sessions: bool = False


def _get_runner(request: Request) -> KimiCLIRunner:
    return request.app.state.runner


def _model_key(provider_key: str, model_id: str, existing: dict[str, LLMModel]) -> str:
    """Derive a unique config key for a model.

    Prefer the bare model id (matches existing keys like ``kimi-for-coding``);
    fall back to a provider-namespaced key on collision.
    """
    base = _MODEL_KEY_RE.sub("-", model_id).strip("-") or "model"
    if base not in existing:
        return base
    namespaced = f"{provider_key}-{base}"
    key = namespaced
    suffix = 2
    while key in existing:
        key = f"{namespaced}-{suffix}"
        suffix += 1
    return key


def _caps_from_payload(item: dict[str, Any], model_id: str) -> list[str] | None:
    """Derive capabilities from a ``/models`` payload item, then fall back to
    name-based heuristics via :func:`derive_model_capabilities`."""
    caps: set[str] = set()
    if item.get("supports_reasoning"):
        caps.add("thinking")
    if item.get("supports_image_in"):
        caps.add("image_in")
    if item.get("supports_video_in"):
        caps.add("video_in")
    lowered = model_id.lower()
    if "thinking" in lowered or "reason" in lowered:
        caps.update(("thinking", "always_thinking"))
    if not caps:
        # Delegate to the LLM-side name heuristics (kimi-k2/k3/highspeed rules)
        derived = derive_model_capabilities(
            LLMModel(provider="_", model=model_id, max_context_size=0)
        )
        caps.update(cast(set[str], derived))
    return sorted(caps) if caps else None


async def _fetch_remote_models(
    base_url: str,
    api_key: str,
) -> list[ProviderModelSpec]:
    """Probe ``{base_url}/models`` (OpenAI-compatible shape)."""
    url = base_url.rstrip("/") + "/models"
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Never follow redirects: a validated https URL must not bounce the
        # request (with its Authorization header) to an internal/plain host.
        async with session.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            allow_redirects=False,
        ) as resp:
            if resp.status != 200:
                body = (await resp.text())[:300]
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch models from {url}: HTTP {resp.status} {body}",
                )
            payload = await resp.json()
    data = payload.get("data")
    if not isinstance(data, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unexpected /models response from {url}",
        )
    models: list[ProviderModelSpec] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if not model_id:
            continue
        context_length = int(item.get("context_length") or 0) or 262144
        display = item.get("display_name") or item.get("name")
        models.append(
            ProviderModelSpec(
                model=str(model_id),
                max_context_size=context_length,
                capabilities=_caps_from_payload(item, str(model_id)),
                display_name=str(display) if display else None,
            )
        )
    if not models:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"No models returned by {url}",
        )
    return models


def _provider_info(key: str, provider: LLMProvider, models: dict[str, LLMModel]) -> ProviderInfo:
    owned = [(k, m) for k, m in models.items() if m.provider == key]
    return ProviderInfo(
        key=key,
        type=provider.type,
        base_url=provider.base_url,
        has_api_key=bool(provider.api_key.get_secret_value()),
        models=[
            ProviderModelSpec(
                model=m.model,
                max_context_size=m.max_context_size,
                capabilities=sorted(m.capabilities) if m.capabilities else None,
                display_name=m.display_name,
            )
            for _, m in owned
        ],
        model_keys=[k for k, _ in owned],
    )


def _build_list_response() -> ProviderListResponse:
    config = load_config()
    return ProviderListResponse(
        default_model=config.default_model,
        default_thinking=config.default_thinking,
        providers=[
            _provider_info(key, provider, config.models)
            for key, provider in config.providers.items()
        ],
    )


@router.get("/", summary="List providers and their models")
async def list_providers(_: JWTUser = Depends(require_user)) -> ProviderListResponse:
    return _build_list_response()


@router.post("/", summary="Add a provider (models fetched from /models when omitted)")
async def create_provider(
    request: ProviderUpsertRequest,
    _: JWTUser = Depends(require_admin),
) -> ProviderListResponse:
    if not _PROVIDER_KEY_RE.match(request.key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider key must be alphanumeric with optional - or _",
        )
    async with _config_lock:
        config = load_config()
        if request.key in config.providers:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Provider '{request.key}' already exists",
            )

        models = request.models
        if models is None:
            if not request.api_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="api_key is required to auto-fetch models",
                )
            await _validate_fetch_url(request.base_url)
            models = await _fetch_remote_models(request.base_url, request.api_key)

        config.providers[request.key] = LLMProvider(
            type=cast(Any, request.type),
            base_url=request.base_url,
            api_key=SecretStr(request.api_key or ""),
            custom_headers=request.custom_headers,
            reasoning_key=request.reasoning_key,
        )
        for spec in models:
            key = _model_key(request.key, spec.model, config.models)
            config.models[key] = LLMModel(
                provider=request.key,
                model=spec.model,
                max_context_size=spec.max_context_size,
                capabilities=cast(set[ModelCapability], set(spec.capabilities)) if spec.capabilities else None,
                display_name=spec.display_name,
            )
        if not config.default_model and config.models:
            config.default_model = next(iter(config.models))
        save_config(config)
    return _build_list_response()


@router.put("/{key}", summary="Update a provider's endpoint, key, or models")
async def update_provider(
    key: str,
    request: ProviderUpsertRequest,
    _: JWTUser = Depends(require_admin),
) -> ProviderListResponse:
    # L15: the body key must agree with the path key to avoid confusing writes.
    if request.key != key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Body key must match the path key",
        )
    async with _config_lock:
        config = load_config()
        provider = config.providers.get(key)
        if provider is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider '{key}' not found",
            )

        provider.base_url = request.base_url
        provider.type = cast(Any, request.type)
        # L15: None keeps the stored key; an explicit empty string clears it.
        if request.api_key is not None:
            provider.api_key = SecretStr(request.api_key)
        if request.custom_headers is not None:
            provider.custom_headers = request.custom_headers
        if request.reasoning_key is not None:
            provider.reasoning_key = request.reasoning_key

        if request.models is not None:
            # Replace the provider's model set.
            for model_key in [k for k, m in config.models.items() if m.provider == key]:
                del config.models[model_key]
            for spec in request.models:
                model_key = _model_key(key, spec.model, config.models)
                config.models[model_key] = LLMModel(
                    provider=key,
                    model=spec.model,
                    max_context_size=spec.max_context_size,
                    capabilities=cast(set[ModelCapability], set(spec.capabilities))
                    if spec.capabilities
                    else None,
                    display_name=spec.display_name,
                )
            if config.default_model not in config.models:
                config.default_model = next(iter(config.models), "")

        save_config(config)
    return _build_list_response()


@router.delete("/{key}", summary="Delete a provider and its models")
async def delete_provider(
    key: str,
    _: JWTUser = Depends(require_admin),
) -> ProviderListResponse:
    async with _config_lock:
        config = load_config()
        if key not in config.providers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider '{key}' not found",
            )
        default_model = config.models.get(config.default_model)
        if default_model is not None and default_model.provider == key:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete the provider of the default model; switch the default first",
            )
        for model_key in [k for k, m in config.models.items() if m.provider == key]:
            del config.models[model_key]
        del config.providers[key]
        save_config(config)
    return _build_list_response()


@router.post("/fetch-models", summary="Probe {base_url}/models for a provider")
async def fetch_models(
    request: FetchModelsRequest,
    user: JWTUser = Depends(require_user),
) -> FetchModelsResponse:
    api_key = request.api_key
    if not api_key and request.provider_key:
        # Reusing a stored key: pin the URL to the provider's stored base_url
        # so the key can never be exfiltrated to an attacker-controlled URL (C1).
        config = load_config()
        provider = config.providers.get(request.provider_key)
        if provider is not None:
            if _normalize_base_url(request.base_url) != _normalize_base_url(provider.base_url):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="base_url must match the provider's stored base_url when reusing its key",
                )
            api_key = provider.api_key.get_secret_value()
    else:
        # Probing an arbitrary URL is an SSRF vector: admins only, with guards.
        from cran_code.web.db.models import UserRole

        if user.role != UserRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator role required to probe arbitrary provider URLs",
            )
        await _validate_fetch_url(request.base_url)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key (or an existing provider_key with a stored key) is required",
        )
    models = await _fetch_remote_models(request.base_url, api_key)
    return FetchModelsResponse(models=models)


@router.post(
    "/models/{model_key}/context",
    summary="Set a model's context window (e.g. K3 256K/512K/1M tiers)",
)
async def set_model_context(
    model_key: str,
    request: ModelContextRequest,
    _: JWTUser = Depends(require_admin),
    runner: KimiCLIRunner = Depends(_get_runner),
) -> ProviderListResponse:
    async with _config_lock:
        config = load_config()
        model = config.models.get(model_key)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model '{model_key}' not found",
            )
        model.max_context_size = request.max_context_size
        save_config(config)
    if request.restart_running_sessions:
        # Running workers created their LLM with the old context size.
        await runner.restart_running_workers(reason="config_update", force=False)
    return _build_list_response()


@router.post("/select", summary="Switch the global default model (restarts running workers)")
async def select_model(
    request: SelectModelRequest,
    _: JWTUser = Depends(require_admin),
    runner: KimiCLIRunner = Depends(_get_runner),
) -> SelectModelResponse:
    async with _config_lock:
        config = load_config()
        if request.default_model not in config.models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{request.default_model}' not found in config",
            )
        config.default_model = request.default_model
        if request.default_thinking is not None:
            config.default_thinking = request.default_thinking
        save_config(config)

    restarted: list[str] = []
    skipped_busy: list[str] = []
    if request.restart_running_sessions:
        # cc-switch issue #3057: live sessions keep the old provider unless
        # workers are restarted — always restart after a switch.
        summary = await runner.restart_running_workers(
            reason="config_update",
            force=request.force_restart_busy_sessions,
        )
        restarted = [str(sid) for sid in summary.restarted_session_ids]
        skipped_busy = [str(sid) for sid in summary.skipped_busy_session_ids]

    return SelectModelResponse(
        default_model=config.default_model,
        default_thinking=config.default_thinking,
        restarted_session_ids=restarted or None,
        skipped_busy_session_ids=skipped_busy or None,
    )
