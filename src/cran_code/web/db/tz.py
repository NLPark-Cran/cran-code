"""Timezone helpers for usage bucketing.

SQLite has no time-zone database, so daily usage buckets are computed by
shifting ``created_at`` (stored in UTC) by the zone's *current* UTC offset.
For zones with DST this means historical rows near a transition can land one
hour off — acceptable for usage statistics; documented behavior.

A team can pin a display timezone (``teams.timezone``, IANA name); personal
views default to the caller's browser timezone passed as a query param.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TZ = "UTC"


def validate_tz_name(tz: str) -> str:
    """Validate an IANA timezone name, returning it unchanged.

    Raises ValueError for unknown names.
    """
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown timezone: {tz}") from exc
    return tz


def utc_offset_minutes(tz: str | None) -> int:
    """Current UTC offset of the zone in minutes (UTC when tz is None)."""
    if not tz:
        return 0
    return int(ZoneInfo(tz).utcoffset(datetime.now(UTC)).total_seconds() // 60)


def sqlite_shift_modifier(tz: str | None) -> str:
    """SQLite datetime modifier that shifts a UTC timestamp into local time."""
    minutes = utc_offset_minutes(tz)
    return f"{minutes:+d} minutes"


def local_day_start_utc(tz: str | None, days: int) -> datetime:
    """UTC instant of the start of the earliest local calendar day in range.

    ``days=1`` → start of the current local day ("today" in that zone).
    """
    days = max(1, days)
    offset = timedelta(minutes=utc_offset_minutes(tz))
    local_now = datetime.now(UTC) + offset
    local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    local_start -= timedelta(days=days - 1)
    return local_start - offset
