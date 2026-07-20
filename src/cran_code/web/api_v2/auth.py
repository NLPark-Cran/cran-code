"""Authentication API: register, login, refresh."""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from cran_code.web.auth_v2 import create_access_token, hash_password, verify_password
from cran_code.web.db import AsyncSessionLocal, User

router = APIRouter(prefix="/api/v2/auth", tags=["auth"])

# Sliding-window rate limit for credential endpoints (in-memory, per client IP).
_RATE_LIMIT_ATTEMPTS = 10
_RATE_LIMIT_WINDOW_SECONDS = 60.0
_rate_limit_buckets: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    """Resolve the client IP.

    X-Forwarded-For is only trusted when the immediate peer is loopback
    (i.e. the local Nginx reverse proxy); otherwise a client could spoof the
    header to reset its rate-limit window.
    """
    peer = request.client.host if request.client else ""
    if peer in ("127.0.0.1", "::1"):
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            first_hop = forwarded_for.split(",")[0].strip()
            if first_hop:
                return first_hop
    return peer or "unknown"


def _check_rate_limit(request: Request) -> None:
    """Enforce max 10 attempts per minute per client IP (sliding window).

    Single-process asyncio server: a plain dict of timestamps is sufficient.
    The bucket dict is pruned so it cannot grow unboundedly with distinct IPs.
    """
    now = time.monotonic()
    if len(_rate_limit_buckets) > 10_000:
        cutoff = now - _RATE_LIMIT_WINDOW_SECONDS
        for ip in [ip for ip, ts in _rate_limit_buckets.items() if not ts or ts[-1] < cutoff]:
            del _rate_limit_buckets[ip]
    ip = _client_ip(request)
    attempts = [
        ts for ts in _rate_limit_buckets.get(ip, []) if now - ts < _RATE_LIMIT_WINDOW_SECONDS
    ]
    if len(attempts) >= _RATE_LIMIT_ATTEMPTS:
        _rate_limit_buckets[ip] = attempts
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please try again later.",
        )
    attempts.append(now)
    _rate_limit_buckets[ip] = attempts


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str | None = Field(None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    display_name: str | None
    avatar_url: str | None
    role: str
    created_at: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, request: Request) -> TokenResponse:
    _check_rate_limit(request)
    async with AsyncSessionLocal() as session:
        # Check if email or username already exists
        existing = await session.execute(
            select(User).where((User.email == req.email) | (User.username == req.username))
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email or username already registered",
            )

        user = User(
            email=req.email,
            username=req.username,
            password_hash=hash_password(req.password),
            display_name=req.display_name or req.username,
        )
        session.add(user)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email or username already registered",
            ) from exc
        await session.refresh(user)

        token = create_access_token(str(user.id))
        return TokenResponse(
            access_token=token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                role=user.role.value,
                created_at=user.created_at.isoformat(),
            ),
        )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request) -> TokenResponse:
    _check_rate_limit(request)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == req.email))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        token = create_access_token(str(user.id))
        return TokenResponse(
            access_token=token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
                role=user.role.value,
                created_at=user.created_at.isoformat(),
            ),
        )
