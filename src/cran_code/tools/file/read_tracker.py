"""Read-before-write discipline: track files the agent has read this process.

Ported idea from kimi-code 0.38.0: `WriteFile`/`StrReplaceFile` must not modify
an existing file the agent has never read in this session — blind overwrites
are a common source of destroyed user work. New-file creation is unaffected.

The tracker is intentionally process-local (per worker): after a worker
restart the agent simply gets a clear "read it first" error and recovers.
"""

from __future__ import annotations

_read_files: set[str] = set()
"""Canonical string paths read (or freshly written) in this process."""


def mark_read(path: object) -> None:
    """Mark a canonical path as known-to-agent (after ReadFile or a write)."""
    _read_files.add(str(path))


def has_read(path: object) -> bool:
    """Whether the agent has read (or written) this canonical path before."""
    return str(path) in _read_files


def clear_read_tracker() -> None:
    """Reset the tracker. For tests."""
    _read_files.clear()


def not_read_error(path: object) -> str:
    """Standard guidance message for unread-file modification attempts."""
    return (
        f"`{path}` has not been read in this session. "
        "Call ReadFile on it first to avoid blind overwrites, then retry."
    )
