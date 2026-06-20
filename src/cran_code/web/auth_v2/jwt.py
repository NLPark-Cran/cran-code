"""JWT token creation and validation."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cran_code.web.db import AsyncSessionLocal, User

if TYPE_CHECKING:
    from fastapi import Request

_SECRET_KEY = os.environ.get("CRAN_JWT_SECRET")
if not _SECRET_KEY:
    import secrets

    _SECRET_KEY = secrets.token_urlsafe(32)
    # Dev-only ephemeral key; production MUST set CRAN_JWT_SECRET
    import logging

    logging.getLogger("cran_code.auth").warning(
        "CRAN_JWT_SECRET not set; using ephemeral dev key. "
        "All tokens will invalidate on restart. Set CRAN_JWT_SECRET for persistent auth."
    )
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_DAYS = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v2/auth/login", auto_error=False)


class TokenPayload(BaseModel):
    sub: str | None = None  # user id
    exp: datetime | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(days=_ACCESS_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, _SECRET_KEY, algorithm=_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
        return TokenPayload(sub=payload.get("sub"), exp=payload.get("exp"))
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
) -> User | None:
    if token is None:
        return None
    payload = decode_token(token)
    if payload.sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == payload.sub))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user


async def require_user(token: str | None = Depends(oauth2_scheme)) -> User:
    user = await get_current_user(token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
