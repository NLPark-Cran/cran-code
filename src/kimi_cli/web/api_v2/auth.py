"""Authentication API: register, login, refresh."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from kimi_cli.web.auth_v2 import create_access_token, hash_password, verify_password
from kimi_cli.web.db import AsyncSessionLocal, User

router = APIRouter(prefix="/api/v2/auth", tags=["auth"])


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
async def register(req: RegisterRequest) -> TokenResponse:
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
async def login(req: LoginRequest) -> TokenResponse:
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
