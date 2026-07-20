"""Provider API key resolution and quota accounting.

Resolution order for a (user, provider) pair:

1. ``personal`` — the user's own :class:`UserProviderKey`.
2. ``team`` — a :class:`TeamProviderKey` of any team the user belongs to
   (first match by creation time).
3. ``shared`` — the global key from ``config.toml``, when the provider's
   sharing policy allows this user.
4. ``None`` — no usable key.

Quota exhaustion is deliberately *not* part of key resolution; use
:func:`remaining_quota` / :func:`quota_summary` for that.
"""

from __future__ import annotations

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from cran_code.config import load_config
from cran_code.web.db.connection import AsyncSessionLocal
from cran_code.web.db.models import (
    ProviderGrant,
    ProviderPolicy,
    TeamMember,
    TeamProviderKey,
    UsageRecord,
    User,
    UserProviderKey,
    UserRole,
)

KeySource = str  # "personal" | "team" | "shared"


def _global_api_key(provider_key: str) -> str | None:
    """Return the non-empty global API key for a provider, or ``None``."""
    provider = load_config().providers.get(provider_key)
    if provider is None:
        return None
    api_key = provider.api_key.get_secret_value()
    return api_key or None


async def _is_global_admin(session: AsyncSession, user_id: str) -> bool:
    user = await session.get(User, user_id)
    return user is not None and user.role == UserRole.admin


async def _matching_grants(
    session: AsyncSession,
    provider_key: str,
    user_id: str,
    team_ids: list[str],
) -> list[ProviderGrant]:
    """Grants covering this user directly or via any of their teams."""
    conditions = [
        and_(
            ProviderGrant.subject_type == "user",
            ProviderGrant.subject_id == user_id,
        )
    ]
    if team_ids:
        conditions.append(
            and_(
                ProviderGrant.subject_type == "team",
                ProviderGrant.subject_id.in_(team_ids),
            )
        )
    result = await session.execute(
        select(ProviderGrant).where(
            ProviderGrant.provider_key == provider_key,
            or_(*conditions),
        )
    )
    return list(result.scalars().all())


async def _shared_allowed(
    session: AsyncSession,
    provider_key: str,
    user_id: str,
    team_ids: list[str],
) -> bool:
    """Whether the sharing policy lets this user use the global key.

    Quota exhaustion is intentionally not checked here.
    """
    policy = await session.get(ProviderPolicy, provider_key)
    mode = policy.shared_mode if policy is not None else "all"
    if mode == "all":
        return True
    if await _is_global_admin(session, user_id):
        return True
    return bool(await _matching_grants(session, provider_key, user_id, team_ids))


async def resolve_provider_key(
    user_id: str,
    provider_key: str,
    team_ids: list[str],
) -> tuple[str, KeySource] | None:
    """Resolve the API key a user should use for a provider.

    Returns ``(api_key, source)`` where ``source`` is ``"personal"``,
    ``"team"`` or ``"shared"``, or ``None`` when no key is usable. See the
    module docstring for the resolution order.
    """
    async with AsyncSessionLocal() as session:
        # 1. Personal key
        result = await session.execute(
            select(UserProviderKey).where(
                UserProviderKey.user_id == user_id,
                UserProviderKey.provider_key == provider_key,
            )
        )
        personal = result.scalar_one_or_none()
        if personal is not None:
            return (personal.api_key, "personal")

        # 2. Team key (first match by creation time)
        if team_ids:
            result = await session.execute(
                select(TeamProviderKey)
                .where(
                    TeamProviderKey.provider_key == provider_key,
                    TeamProviderKey.team_id.in_(team_ids),
                )
                .order_by(TeamProviderKey.created_at)
            )
            team_key = result.scalars().first()
            if team_key is not None:
                return (team_key.api_key, "team")

        # 3. Shared global key (policy-gated; quota not checked here)
        api_key = _global_api_key(provider_key)
        if api_key is not None and await _shared_allowed(
            session, provider_key, user_id, team_ids
        ):
            return (api_key, "shared")

        return None


async def get_key_status(
    user: User,
    provider_key: str,
    team_ids: list[str],
) -> str:
    """Return ``"personal"``/``"team"``/``"shared"``/``"none"`` for API display."""
    resolved = await resolve_provider_key(user.id, provider_key, team_ids)
    if resolved is None:
        return "none"
    return resolved[1]


async def _used_shared_tokens(
    session: AsyncSession,
    provider_key: str,
    grant: ProviderGrant,
) -> int:
    """Tokens consumed with ``source='shared'`` by the grant's subject.

    For a user subject: that user's shared usage. For a team subject: the
    shared usage of all current members of that team.
    """
    total = func.coalesce(
        func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens), 0
    )
    if grant.subject_type == "team":
        member_ids = (
            select(TeamMember.user_id)
            .where(TeamMember.team_id == grant.subject_id)
            .scalar_subquery()
        )
        stmt = select(total).where(
            UsageRecord.provider_key == provider_key,
            UsageRecord.source == "shared",
            UsageRecord.user_id.in_(member_ids),
        )
    else:
        stmt = select(total).where(
            UsageRecord.provider_key == provider_key,
            UsageRecord.source == "shared",
            UsageRecord.user_id == grant.subject_id,
        )
    result = await session.execute(stmt)
    return int(result.scalar_one())


async def quota_summary(
    user_id: str,
    provider_key: str,
    team_ids: list[str],
) -> tuple[int | None, int | None]:
    """Return ``(quota_tokens, remaining_tokens)`` for shared usage.

    Semantics:

    - ``(None, None)`` ("no limit applies") when the provider's
      ``shared_mode`` is not ``"restricted"`` (the default), when the user is
      a global admin, or when no grant covers the user.
    - ``(None, None)`` also when any covering grant has a ``NULL``
      ``quota_tokens`` (an unlimited grant wins).
    - Otherwise, for each covering grant the remaining tokens are
      ``quota_tokens - used`` where ``used`` is the sum of
      ``input_tokens + output_tokens`` of :class:`UsageRecord` rows with
      ``source='shared'`` for the grant's subject (the user, or all members
      of the granted team). The user is constrained by the most restrictive
      grant, so the result is ``(min quota, min remaining)`` across grants.
    """
    async with AsyncSessionLocal() as session:
        policy = await session.get(ProviderPolicy, provider_key)
        mode = policy.shared_mode if policy is not None else "all"
        if mode != "restricted":
            return (None, None)
        if await _is_global_admin(session, user_id):
            return (None, None)
        grants = await _matching_grants(session, provider_key, user_id, team_ids)
        if not grants:
            return (None, None)
        if any(g.quota_tokens is None for g in grants):
            return (None, None)
        quotas = [g.quota_tokens for g in grants if g.quota_tokens is not None]
        remainings: list[int] = []
        for grant in grants:
            if grant.quota_tokens is None:
                continue
            used = await _used_shared_tokens(session, provider_key, grant)
            remainings.append(grant.quota_tokens - used)
        return (min(quotas), min(remainings))


async def remaining_quota(
    user_id: str,
    provider_key: str,
    team_ids: list[str],
) -> int | None:
    """Remaining shared tokens for this user; ``None`` means no limit applies.

    This is the ``remaining_tokens`` half of :func:`quota_summary`; see its
    docstring for the exact semantics.
    """
    _, remaining = await quota_summary(user_id, provider_key, team_ids)
    return remaining
