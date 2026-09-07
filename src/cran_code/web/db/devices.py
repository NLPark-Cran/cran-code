"""Device store for the Luoshu reverse tunnel (ADR 004).

A *device* is a Luoshu instance running on a user's machine. The raw device
token is a 64-char random hex string returned exactly once at creation; only
its SHA-256 hex digest is persisted (tokens are high-entropy, so plain
SHA-256 — no password KDF — is the right primitive, and lookups stay O(1) via
the unique index).

All functions open their own session via the module-level ``AsyncSessionLocal``
so tests can patch a single point (same pattern as ``db/memories.py``).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime

from sqlalchemy import select

from cran_code.web.db.connection import AsyncSessionLocal
from cran_code.web.db.models import Device

MAX_DEVICE_NAME_LENGTH = 100


def hash_token(token: str) -> str:
    """SHA-256 hex digest of a raw device token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_device(user_id: str, name: str) -> tuple[Device, str]:
    """Register a device. Returns ``(device, raw_token)`` — the raw token is
    never stored and never returned again."""
    name = name.strip()[:MAX_DEVICE_NAME_LENGTH]
    if not name:
        raise ValueError("device name must not be empty")
    raw_token = secrets.token_hex(32)
    async with AsyncSessionLocal() as session:
        device = Device(user_id=user_id, name=name, token_hash=hash_token(raw_token))
        session.add(device)
        await session.commit()
        await session.refresh(device)
        return device, raw_token


async def list_for_user(user_id: str) -> list[Device]:
    """Active (non-revoked) devices of a user, newest first."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Device)
            .where(Device.user_id == user_id, Device.revoked.is_(False))
            .order_by(Device.created_at.desc(), Device.id.desc())
        )
        return list(result.scalars().all())


async def get_owned(user_id: str, device_id: str) -> Device | None:
    """Fetch an active device owned by ``user_id`` (None when not found/owned)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Device).where(
                Device.id == device_id,
                Device.user_id == user_id,
                Device.revoked.is_(False),
            )
        )
        return result.scalar_one_or_none()


async def revoke(user_id: str, device_id: str) -> Device | None:
    """Revoke (never hard-delete) a device owned by ``user_id``."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Device).where(
                Device.id == device_id,
                Device.user_id == user_id,
                Device.revoked.is_(False),
            )
        )
        device = result.scalar_one_or_none()
        if device is None:
            return None
        device.revoked = True
        await session.commit()
        await session.refresh(device)
        return device


async def authenticate(device_id: str, token: str) -> Device | None:
    """Validate a tunnel credential: the token must hash to the stored digest
    of the *active* device ``device_id``. Constant-time comparison."""
    if not token:
        return None
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Device).where(Device.id == device_id, Device.revoked.is_(False))
        )
        device = result.scalar_one_or_none()
        if device is None:
            return None
        if not hmac.compare_digest(device.token_hash, hash_token(token)):
            return None
        return device


async def touch_last_seen(device_id: str) -> None:
    """Best-effort liveness timestamp (tunnel connect + every relayed message)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if device is not None:
            device.last_seen_at = datetime.now(UTC)
            await session.commit()
