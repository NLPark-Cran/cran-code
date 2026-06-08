"""User profile API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from cran_code.web.auth_v2.jwt import User, require_user
from cran_code.web.db import AsyncSessionLocal

router = APIRouter(prefix="/api/v2/users", tags=["users"])


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)


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


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(require_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        display_name=current_user.display_name,
        avatar_url=current_user.avatar_url,
        role=current_user.role.value,
        created_at=current_user.created_at.isoformat(),
    )


@router.patch("/me", response_model=UserResponse)
async def update_me(
    req: UserProfileUpdate,
    current_user: User = Depends(require_user),
) -> UserResponse:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one()
        if req.display_name is not None:
            user.display_name = req.display_name
        if req.avatar_url is not None:
            user.avatar_url = req.avatar_url
        await session.commit()
        await session.refresh(user)
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            role=user.role.value,
            created_at=user.created_at.isoformat(),
        )
