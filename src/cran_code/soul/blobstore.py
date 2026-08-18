"""Externalize large inline media (``data:`` URLs) to content-addressed blob files.

Context persistence (``context.jsonl``) stores ``blobref:<sha256>.<ext>`` references
instead of multi-MB base64 payloads; restoration rehydrates them back to ``data:``
URLs. In-memory messages, wire events and provider serialization are unaffected.

Layout: blobs live in a ``blobs/`` directory next to ``context.jsonl`` (for legacy
session files, ``<stem>.blobs/``). Files are content-addressed, so duplicate media
is stored once and fork/copy operations can safely hardlink or copy by name.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
from pathlib import Path
from typing import Any

from cran_code.utils.logging import logger

BLOBREF_SCHEME = "blobref:"
"""URL scheme used in persisted context for externalized media."""

EXTERNALIZE_MIN_URL_LEN = 1024
"""Only ``data:`` URLs at least this long are externalized."""

_MEDIA_URL_KEYS = ("image_url", "audio_url", "video_url")

_BLOB_NAME_RE = re.compile(r"^[0-9a-f]{64}\.[a-z0-9]{1,8}$")
_BLOBREF_IN_TEXT_RE = re.compile(r"blobref:([0-9a-f]{64}\.[a-z0-9]{1,8})")

_EXT_BY_MIME = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/bmp": "bmp",
    "image/svg+xml": "svg",
    "audio/aac": "aac",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/ogg": "ogg",
    "video/mp4": "mp4",
    "video/webm": "webm",
    "video/quicktime": "mov",
}
_MIME_BY_EXT = {v: k for k, v in _EXT_BY_MIME.items()}


def blobs_dir_for(context_file: Path) -> Path:
    """Return the blob directory associated with a context file."""
    if context_file.name == "context.jsonl":
        return context_file.parent / "blobs"
    # Legacy session file layout: <sessions_dir>/<session_id>.jsonl
    return context_file.parent / f"{context_file.stem}.blobs"


def find_blobrefs(text: str) -> set[str]:
    """Extract blob file names referenced in a raw JSON line."""
    return set(_BLOBREF_IN_TEXT_RE.findall(text))


def externalize_message_dict(data: dict[str, Any], blobs_dir: Path) -> dict[str, Any]:
    """Replace large inline ``data:`` URLs in a serialized message dict with blobrefs.

    Writes blob files as a side effect. Mutates and returns ``data``.
    """
    content = data.get("content")
    if not isinstance(content, list):
        return data
    for part in content:
        if not isinstance(part, dict):
            continue
        for key in _MEDIA_URL_KEYS:
            payload = part.get(key)
            if isinstance(payload, dict):
                url = payload.get("url")
                if isinstance(url, str):
                    new_url = _externalize_url(url, blobs_dir)
                    if new_url is not None:
                        payload["url"] = new_url
    return data


def rehydrate_message_dict(data: dict[str, Any], blobs_dir: Path) -> dict[str, Any]:
    """Replace blobrefs in a raw context line dict with ``data:`` URLs.

    Missing or invalid blobs are replaced with a text placeholder part so that
    restoration never crashes and the LLM never sees an unusable URL.
    Mutates and returns ``data``.
    """
    content = data.get("content")
    if not isinstance(content, list):
        return data
    for i, part in enumerate(content):
        if not isinstance(part, dict):
            continue
        for key in _MEDIA_URL_KEYS:
            payload = part.get(key)
            if isinstance(payload, dict):
                url = payload.get("url")
                if isinstance(url, str) and url.startswith(BLOBREF_SCHEME):
                    content[i] = _rehydrate_part(part, payload, url, blobs_dir)
                break
    return data


def _externalize_url(url: str, blobs_dir: Path) -> str | None:
    if len(url) < EXTERNALIZE_MIN_URL_LEN or not url.startswith("data:"):
        return None
    header, sep, payload = url.partition(",")
    if not sep:
        return None
    mime_spec = header[len("data:") :]
    if not mime_spec.lower().endswith(";base64"):
        return None
    mime = mime_spec[: -len(";base64")].split(";")[0].strip().lower()
    try:
        raw = base64.b64decode(payload)
    except (binascii.Error, ValueError):
        return None
    digest = hashlib.sha256(raw).hexdigest()
    ext = _EXT_BY_MIME.get(mime, "bin")
    try:
        blobs_dir.mkdir(parents=True, exist_ok=True)
        path = blobs_dir / f"{digest}.{ext}"
        if not path.exists():
            tmp_path = path.with_name(path.name + ".tmp")
            tmp_path.write_bytes(raw)
            tmp_path.replace(path)
    except OSError as exc:
        logger.warning("Failed to write media blob, keeping inline: {error}", error=exc)
        return None
    return f"{BLOBREF_SCHEME}{digest}.{ext}"


def _rehydrate_part(
    part: dict[str, Any],
    payload: dict[str, Any],
    url: str,
    blobs_dir: Path,
) -> dict[str, Any]:
    name = url[len(BLOBREF_SCHEME) :]
    if not _BLOB_NAME_RE.match(name):
        logger.warning("Invalid blob reference: {url}", url=url[:80])
        return _blob_missing_placeholder()
    path = blobs_dir / name
    try:
        raw = path.read_bytes()
    except OSError:
        logger.warning("Media blob missing: {path}", path=path)
        return _blob_missing_placeholder()
    mime = _MIME_BY_EXT.get(path.suffix[1:].lower(), "application/octet-stream")
    payload["url"] = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
    return part


def _blob_missing_placeholder() -> dict[str, Any]:
    return {"type": "text", "text": "[media unavailable: blob file missing]"}
