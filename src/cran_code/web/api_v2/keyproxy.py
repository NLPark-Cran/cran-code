"""Provider key proxy: lets workers use team/shared keys without seeing them.

Workers that should use a non-personal provider key (team or shared global
key) are spawned with ``OPENAI_BASE_URL=http://127.0.0.1:<port>/px/v1`` and
``OPENAI_API_KEY=cwk_<token>`` instead of the real key. This router validates
the token, re-resolves the real key server-side (so revocation and policy
changes take effect immediately), enforces shared-key quotas, forwards the
request to the upstream provider, and records token usage.

Tokens are HMAC-signed, so no extra DB table is needed; they carry only
``(user_id, provider_key, source)`` and never key material.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import aiohttp
from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from cran_code import logger
from cran_code.config import load_config
from cran_code.web.db.connection import AsyncSessionLocal
from cran_code.web.db.keys import remaining_quota, resolve_provider_key
from cran_code.web.db.models import TeamMember, UsageRecord

router = APIRouter(prefix="/px/v1", tags=["keyproxy"])

_TOKEN_PREFIX = "cwk_"
# Tokens are placed in worker env vars, so they must expire: an exfiltrated
# token (e.g. via prompt injection into a session's Shell tool) must not work
# forever. Workers restart on model switches and pick up a fresh token.
_TOKEN_TTL_SECONDS = 3 * 24 * 3600
# Only these upstream endpoints may be reached through the proxy.
_ALLOWED_PATHS = frozenset(
    {"chat/completions", "completions", "responses", "models", "embeddings"}
)
# Cap upstream responses we are willing to buffer for non-streaming calls.
_MAX_UPSTREAM_BYTES = 64 * 1024 * 1024


def _proxy_secret() -> bytes:
    """HMAC secret for proxy tokens — the same key that signs user JWTs.

    Falls back to the JWT module's ephemeral random key when CRAN_JWT_SECRET
    is unset (never a hardcoded constant, so tokens stay unforgeable).
    """
    from cran_code.web.auth_v2 import jwt as _jwt

    return str(_jwt._SECRET_KEY).encode("utf-8")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def mint_proxy_token(user_id: str, provider_key: str, source: str) -> str:
    """Mint a worker credential for (user, provider, key source)."""
    now = int(time.time())
    payload = _b64url_encode(
        json.dumps(
            {"u": user_id, "p": provider_key, "s": source, "iat": now, "exp": now + _TOKEN_TTL_SECONDS}
        ).encode("utf-8")
    )
    sig = _b64url_encode(hmac.new(_proxy_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{_TOKEN_PREFIX}{payload}.{sig}"


def verify_proxy_token(token: str) -> dict[str, Any] | None:
    """Validate a proxy token; return its claims or ``None``."""
    if not token.startswith(_TOKEN_PREFIX):
        return None
    body = token[len(_TOKEN_PREFIX) :]
    payload, _, sig = body.partition(".")
    if not payload or not sig:
        return None
    expected = _b64url_encode(hmac.new(_proxy_secret(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        claims = json.loads(_b64url_decode(payload))
    except Exception:
        return None
    if not all(isinstance(claims.get(k), str) for k in ("u", "p", "s")):
        return None
    exp = claims.get("exp")
    if not isinstance(exp, int) or exp < time.time():
        return None
    return claims


async def _user_team_ids(user_id: str) -> list[str]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TeamMember.team_id).where(TeamMember.user_id == user_id)
        )
        return [row[0] for row in result.all()]


async def record_usage(
    *,
    user_id: str,
    provider_key: str,
    model: str,
    source: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Persist one usage record (best-effort; never raises)."""
    if input_tokens <= 0 and output_tokens <= 0:
        return
    try:
        async with AsyncSessionLocal() as session:
            session.add(
                UsageRecord(
                    user_id=user_id,
                    provider_key=provider_key,
                    model=model,
                    source=source,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )
            await session.commit()
    except Exception as e:
        logger.warning(f"Failed to record usage: {e}")


def _extract_bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return token.strip() or None


def _usage_from_openai_payload(payload: dict[str, Any]) -> tuple[int, int] | None:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    prompt = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    completion = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    try:
        return (int(prompt), int(completion))
    except (TypeError, ValueError):
        return None


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(path: str, request: Request) -> Response:
    """Forward a provider API call with the resolved real key."""
    # Loopback-only: this endpoint exists for local workers. On public
    # deployments Nginx proxies from 127.0.0.1, so external clients arriving
    # with a non-loopback peer (direct port access) are rejected.
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Loopback only")
    normalized = path.strip("/")
    if normalized not in _ALLOWED_PATHS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Endpoint not proxied"
        )
    token = _extract_bearer(request)
    claims = verify_proxy_token(token) if token else None
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing key proxy credential",
        )
    user_id = claims["u"]
    provider_key = claims["p"]
    token_source = claims["s"]

    team_ids = await _user_team_ids(user_id)
    resolved = await resolve_provider_key(user_id, provider_key, team_ids)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No usable API key for this provider (revoked or policy changed)",
        )
    real_key, source = resolved
    if source != token_source:
        # Resolution priority changed (e.g. a personal key was added); the
        # worker should be restarted to pick up fresh credentials.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Key resolution changed; please restart the session",
        )

    if source == "shared":
        remaining = await remaining_quota(user_id, provider_key, team_ids)
        if remaining is not None and remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Shared-key quota exhausted; ask your administrator for more quota",
            )

    config = load_config()
    provider = config.providers.get(provider_key)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider '{provider_key}' no longer exists",
        )
    target_url = provider.base_url.rstrip("/") + "/" + path

    body = await request.body()
    model = ""
    stream = False
    if body and request.headers.get("content-type", "").startswith("application/json"):
        try:
            payload = json.loads(body)
            if isinstance(payload, dict):
                model = str(payload.get("model") or "")
                stream = bool(payload.get("stream"))
                # Ask upstream to include usage in the final stream chunk so
                # we can meter streamed completions too.
                if stream and path.rstrip("/").endswith("chat/completions"):
                    payload.setdefault("stream_options", {})["include_usage"] = True
                    body = json.dumps(payload).encode("utf-8")
        except (ValueError, AttributeError):
            pass

    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in ("host", "authorization", "content-length", "accept-encoding")
    }
    headers["Authorization"] = f"Bearer {real_key}"
    if provider.custom_headers:
        headers.update(provider.custom_headers)

    timeout = aiohttp.ClientTimeout(total=None, sock_read=300)
    session = aiohttp.ClientSession(timeout=timeout)
    try:
        upstream = await session.request(
            request.method,
            target_url,
            params=dict(request.query_params),
            data=body or None,
            headers=headers,
        )
    except Exception as e:
        await session.close()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream provider request failed: {e}",
        ) from e

    if stream:
        return await _stream_response(session, upstream, user_id, provider_key, model, source)

    usage: tuple[int, int] | None = None
    try:
        data = await upstream.read()
        if upstream.status < 400 and len(data) <= _MAX_UPSTREAM_BYTES:
            try:
                parsed = json.loads(data)
                usage = _usage_from_openai_payload(parsed)
                if usage is not None and not model:
                    model = str(parsed.get("model") or "")
            except ValueError:
                pass
    finally:
        upstream.release()
        await session.close()
    if len(data) > _MAX_UPSTREAM_BYTES:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Upstream response too large"
        )
    if usage is not None:
        await record_usage(
            user_id=user_id,
            provider_key=provider_key,
            model=model,
            source=source,
            input_tokens=usage[0],
            output_tokens=usage[1],
        )
    return Response(
        content=data,
        status_code=upstream.status,
        media_type=upstream.headers.get("content-type"),
    )


async def _stream_response(
    session: aiohttp.ClientSession,
    upstream: aiohttp.ClientResponse,
    user_id: str,
    provider_key: str,
    model: str,
    source: str,
) -> Response:
    """Stream an SSE upstream response, teeing off the usage chunk."""
    from starlette.responses import StreamingResponse

    usage: dict[str, int] = {"input": 0, "output": 0}

    async def gen():
        buffer = b""
        try:
            async for chunk in upstream.content.iter_any():
                buffer += chunk
                # Parse complete SSE lines looking for the usage payload.
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line.startswith(b"data:") or line == b"data: [DONE]":
                        continue
                    try:
                        event = json.loads(line[len(b"data:") :])
                    except ValueError:
                        continue
                    if isinstance(event, dict):
                        found = _usage_from_openai_payload(event)
                        if found is not None:
                            usage["input"], usage["output"] = found
                yield chunk
        finally:
            upstream.release()
            await session.close()
            await record_usage(
                user_id=user_id,
                provider_key=provider_key,
                model=model,
                source=source,
                input_tokens=usage["input"],
                output_tokens=usage["output"],
            )

    return StreamingResponse(
        gen(),
        status_code=upstream.status,
        media_type=upstream.headers.get("content-type", "text/event-stream"),
    )
