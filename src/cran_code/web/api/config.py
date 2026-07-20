"""Config API routes."""

from __future__ import annotations

import tomlkit
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from tomlkit.exceptions import TOMLKitError

from cran_code import logger
from cran_code.config import LLMModel, get_config_file, load_config, save_config
from cran_code.llm import ProviderType, derive_model_capabilities
from cran_code.web.runner.process import KimiCLIRunner

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigModel(LLMModel):
    """Model configuration for frontend."""

    name: str = Field(description="Model key in cran-code config (Config.models)")
    provider_type: ProviderType = Field(description="Provider type (LLMProvider.type)")


class GlobalConfig(BaseModel):
    """Global configuration snapshot for frontend."""

    default_model: str = Field(description="Current default model key")
    default_thinking: bool = Field(description="Current default thinking mode")
    models: list[ConfigModel] = Field(description="All configured models")


class UpdateGlobalConfigRequest(BaseModel):
    """Request to update global config."""

    default_model: str | None = Field(default=None, description="New default model key")
    default_thinking: bool | None = Field(default=None, description="New default thinking mode")
    restart_running_sessions: bool | None = Field(
        default=None, description="Whether to restart running sessions"
    )
    force_restart_busy_sessions: bool | None = Field(
        default=None, description="Whether to force restart busy sessions"
    )


class UpdateGlobalConfigResponse(BaseModel):
    """Response after updating global config."""

    config: GlobalConfig = Field(description="Updated config snapshot")
    restarted_session_ids: list[str] | None = Field(
        default=None, description="IDs of restarted sessions"
    )
    skipped_busy_session_ids: list[str] | None = Field(
        default=None, description="IDs of busy sessions that were skipped"
    )


class ConfigToml(BaseModel):
    """Raw config.toml content."""

    content: str = Field(description="Raw TOML content")
    path: str = Field(description="Path to config file")
    redacted: bool = Field(
        default=False, description="Whether provider API keys were redacted"
    )


class UpdateConfigTomlRequest(BaseModel):
    """Request to update config.toml."""

    content: str = Field(description="New TOML content")


class UpdateConfigTomlResponse(BaseModel):
    """Response after updating config.toml."""

    success: bool = Field(description="Whether the update was successful")
    error: str | None = Field(default=None, description="Error message if failed")
    restarted_session_ids: list[str] | None = Field(
        default=None, description="IDs of restarted sessions"
    )
    skipped_busy_session_ids: list[str] | None = Field(
        default=None, description="IDs of busy sessions that were skipped"
    )


def _build_global_config() -> GlobalConfig:
    """Build GlobalConfig from cran-code config."""
    config = load_config()

    models: list[ConfigModel] = []
    for model_name, model in config.models.items():
        provider = config.providers.get(model.provider)
        if provider is None:
            continue

        # Derive capabilities
        derived_caps = derive_model_capabilities(model)
        capabilities = derived_caps or None

        models.append(
            ConfigModel(
                name=model_name,
                model=model.model,
                provider=model.provider,
                provider_type=provider.type,
                max_context_size=model.max_context_size,
                capabilities=capabilities,
            )
        )

    return GlobalConfig(
        default_model=config.default_model,
        default_thinking=config.default_thinking,
        models=models,
    )


def _get_runner(req: Request) -> KimiCLIRunner:
    """Get CranCLIRunner from FastAPI app state."""
    return req.app.state.runner


def _ensure_sensitive_apis_allowed(request: Request) -> None:
    """Block sensitive config writes when restricted."""
    if getattr(request.app.state, "restrict_sensitive_apis", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sensitive config APIs are disabled in this mode.",
        )


def _redact_toml_api_keys(content: str) -> str:
    """Redact every ``api_key`` value under any ``[providers.*]`` table."""
    try:
        doc = tomlkit.loads(content)
    except TOMLKitError:
        # Unparseable content is returned as-is; the PUT endpoint validates
        # TOML separately, so this only affects hand-edited broken files.
        return content
    providers = doc.get("providers")
    if isinstance(providers, dict):
        for provider in providers.values():
            if isinstance(provider, dict) and "api_key" in provider:
                provider["api_key"] = "***redacted***"
    return tomlkit.dumps(doc)


async def _has_v2_admin(request: Request) -> bool:
    """Return True if the request carries a valid v2 admin JWT.

    Used to let v2 administrators read/write the raw config.toml even on
    public deployments where sensitive APIs are otherwise blocked.
    """
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return False
    try:
        from cran_code.web.auth_v2.jwt import get_current_user

        user = await get_current_user(token.strip())
    except Exception:
        return False
    if user is None:
        return False
    from cran_code.web.db.models import UserRole

    return bool(getattr(user, "role", None) == UserRole.admin)


@router.get("/", summary="Get global (cran-code) config snapshot")
async def get_global_config() -> GlobalConfig:
    """Get global (cran-code) config snapshot."""
    return _build_global_config()


@router.patch("/", summary="Update global (cran-code) default model/thinking")
async def update_global_config(
    request: UpdateGlobalConfigRequest,
    http_request: Request,
    runner: KimiCLIRunner = Depends(_get_runner),
) -> UpdateGlobalConfigResponse:
    """Update global (cran-code) default model/thinking."""
    # Switching the global model restarts workers for ALL users — admin only,
    # same as the v2 providers/select endpoint.
    if not await _has_v2_admin(http_request):
        _ensure_sensitive_apis_allowed(http_request)
    from cran_code.config import config_write_lock

    async with config_write_lock:
        config = load_config()

        # Validate and update default_model
        if request.default_model is not None:
            if request.default_model not in config.models:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Model '{request.default_model}' not found in config",
                )
            config.default_model = request.default_model

        # Update default_thinking
        if request.default_thinking is not None:
            config.default_thinking = request.default_thinking

        # Save config
        save_config(config)

    # Restart running workers to apply config changes
    restarted: list[str] = []
    skipped_busy: list[str] = []

    restart_running = request.restart_running_sessions
    if restart_running is None:
        restart_running = True  # Default to restarting sessions

    if restart_running:
        summary = await runner.restart_running_workers(
            reason="config_update",
            force=request.force_restart_busy_sessions or False,
        )
        restarted = [str(sid) for sid in summary.restarted_session_ids]
        skipped_busy = [str(sid) for sid in summary.skipped_busy_session_ids]

    return UpdateGlobalConfigResponse(
        config=_build_global_config(),
        restarted_session_ids=restarted if restarted else None,
        skipped_busy_session_ids=skipped_busy if skipped_busy else None,
    )


@router.get("/toml", summary="Get cran-code config.toml")
async def get_config_toml(http_request: Request) -> ConfigToml:
    """Get cran-code config.toml (provider API keys redacted)."""
    if not await _has_v2_admin(http_request):
        _ensure_sensitive_apis_allowed(http_request)
    config_file = get_config_file()
    if not config_file.exists():
        return ConfigToml(content="", path=str(config_file))
    content = config_file.read_text(encoding="utf-8")
    return ConfigToml(
        content=_redact_toml_api_keys(content),
        path=str(config_file),
        redacted=True,
    )


@router.put("/toml", summary="Update cran-code config.toml")
async def update_config_toml(
    request: UpdateConfigTomlRequest,
    http_request: Request,
    runner: KimiCLIRunner = Depends(_get_runner),
) -> UpdateConfigTomlResponse:
    """Update cran-code config.toml."""
    if not await _has_v2_admin(http_request):
        _ensure_sensitive_apis_allowed(http_request)
    if "***redacted***" in request.content:
        # L8: a fetch→edit→PUT round-trip on the redacted view would
        # overwrite real keys with the placeholder.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content contains the redaction placeholder; restore real api_key values before saving",
        )
    from cran_code.config import config_write_lock, load_config_from_string

    async with config_write_lock:
        try:
            # Validate the config first
            load_config_from_string(request.content)

            # Write to file
            config_file = get_config_file()
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(request.content, encoding="utf-8")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Failed to update config.toml: {e}")
            return UpdateConfigTomlResponse(success=False, error=str(e))

    # Restart running workers to apply config changes
    restarted: list[str] = []
    skipped_busy: list[str] = []
    summary = await runner.restart_running_workers(reason="config_update", force=False)
    restarted = [str(sid) for sid in summary.restarted_session_ids]
    skipped_busy = [str(sid) for sid in summary.skipped_busy_session_ids]

    return UpdateConfigTomlResponse(
        success=True,
        restarted_session_ids=restarted if restarted else None,
        skipped_busy_session_ids=skipped_busy if skipped_busy else None,
    )
