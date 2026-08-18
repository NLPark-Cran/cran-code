"""Tests for cran_code.soul.blobstore and its Context/fork integration."""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import pytest
from kaos.path import KaosPath
from kosong.message import ImageURLPart, Message, TextPart

from cran_code.session_fork import fork_session
from cran_code.soul.blobstore import (
    blobs_dir_for,
    externalize_message_dict,
    find_blobrefs,
    rehydrate_message_dict,
)
from cran_code.soul.context import Context

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _data_url(payload: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}"


def _big_image_message(payload: bytes) -> Message:
    return Message(
        role="tool",
        tool_call_id="call_1",
        content=[
            TextPart(text="<image path=/tmp/x.png>"),
            ImageURLPart(image_url=ImageURLPart.ImageURL(url=_data_url(payload))),
            TextPart(text="</image>"),
        ],
    )


def _image_part_dict(payload: bytes) -> dict:
    return {
        "type": "image_url",
        "image_url": {"url": _data_url(payload)},
    }


# ---------------------------------------------------------------------------
# blobstore unit tests
# ---------------------------------------------------------------------------


class TestExternalize:
    def test_large_data_url_externalized(self, tmp_path: Path) -> None:
        payload = b"\x89PNG" + b"x" * 5000
        part = _image_part_dict(payload)
        data = {"role": "tool", "content": [part]}

        externalize_message_dict(data, tmp_path / "blobs")

        url = part["image_url"]["url"]
        assert url.startswith("blobref:")
        name = url[len("blobref:") :]
        blob = tmp_path / "blobs" / name
        assert blob.exists()
        assert blob.read_bytes() == payload
        assert name.endswith(".png")

    def test_content_addressed_dedup(self, tmp_path: Path) -> None:
        payload = b"same-bytes" * 500
        part1 = _image_part_dict(payload)
        part2 = _image_part_dict(payload)
        externalize_message_dict({"role": "tool", "content": [part1]}, tmp_path / "blobs")
        externalize_message_dict({"role": "tool", "content": [part2]}, tmp_path / "blobs")
        assert part1["image_url"]["url"] == part2["image_url"]["url"]
        assert len(list((tmp_path / "blobs").iterdir())) == 1

    def test_small_data_url_kept_inline(self, tmp_path: Path) -> None:
        part = {"type": "image_url", "image_url": {"url": _data_url(b"tiny")}}
        data = {"role": "tool", "content": [part]}
        externalize_message_dict(data, tmp_path / "blobs")
        assert part["image_url"]["url"].startswith("data:")
        assert not (tmp_path / "blobs").exists()

    def test_non_base64_data_url_kept_inline(self, tmp_path: Path) -> None:
        url = "data:image/svg+xml," + "%3Csvg%3E" * 500
        part = {"type": "image_url", "image_url": {"url": url}}
        externalize_message_dict({"role": "tool", "content": [part]}, tmp_path / "blobs")
        assert part["image_url"]["url"] == url

    def test_http_url_untouched(self, tmp_path: Path) -> None:
        url = "https://example.com/" + "a" * 5000 + ".png"
        part = {"type": "image_url", "image_url": {"url": url}}
        externalize_message_dict({"role": "tool", "content": [part]}, tmp_path / "blobs")
        assert part["image_url"]["url"] == url

    def test_string_content_untouched(self, tmp_path: Path) -> None:
        data = {"role": "assistant", "content": "plain text"}
        assert externalize_message_dict(data, tmp_path / "blobs") == data


class TestRehydrate:
    def test_roundtrip(self, tmp_path: Path) -> None:
        payload = b"\x89PNG" + b"y" * 5000
        part = _image_part_dict(payload)
        original_url = part["image_url"]["url"]
        blobs = tmp_path / "blobs"
        data = {"role": "tool", "content": [part]}
        externalize_message_dict(data, blobs)

        restored = json.loads(json.dumps(data))
        rehydrate_message_dict(restored, blobs)
        assert restored["content"][0]["image_url"]["url"] == original_url

    def test_missing_blob_becomes_text_placeholder(self, tmp_path: Path) -> None:
        name = "a" * 64 + ".png"
        data = {
            "role": "tool",
            "content": [{"type": "image_url", "image_url": {"url": f"blobref:{name}"}}],
        }
        rehydrate_message_dict(data, tmp_path / "blobs")
        part = data["content"][0]
        assert part["type"] == "text"
        assert "unavailable" in part["text"]

    def test_invalid_blobref_becomes_text_placeholder(self, tmp_path: Path) -> None:
        data = {
            "role": "tool",
            "content": [
                {"type": "image_url", "image_url": {"url": "blobref:../../etc/passwd"}}
            ],
        }
        rehydrate_message_dict(data, tmp_path / "blobs")
        assert data["content"][0]["type"] == "text"

    def test_non_blobref_untouched(self, tmp_path: Path) -> None:
        part = {"type": "image_url", "image_url": {"url": "https://x.test/a.png"}}
        data = {"role": "tool", "content": [part]}
        rehydrate_message_dict(data, tmp_path / "blobs")
        assert data["content"][0]["image_url"]["url"] == "https://x.test/a.png"


class TestHelpers:
    def test_blobs_dir_for_modern_layout(self, tmp_path: Path) -> None:
        assert blobs_dir_for(tmp_path / "sess" / "context.jsonl") == tmp_path / "sess" / "blobs"

    def test_blobs_dir_for_legacy_layout(self, tmp_path: Path) -> None:
        assert blobs_dir_for(tmp_path / "abc.jsonl") == tmp_path / "abc.blobs"

    def test_find_blobrefs(self) -> None:
        name = "b" * 64 + ".jpg"
        assert find_blobrefs(f'{{"url": "blobref:{name}"}}') == {name}
        assert find_blobrefs('{"url": "data:image/png;base64,xyz"}') == set()


# ---------------------------------------------------------------------------
# Context integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_append_externalizes_media_and_restores(tmp_path: Path) -> None:
    path = tmp_path / "context.jsonl"
    path.touch()
    ctx = Context(file_backend=path)

    payload = b"\x89PNG" + b"z" * 5000
    original_url = _data_url(payload)
    await ctx.append_message(_big_image_message(payload))

    # On disk: blobref, no base64 payload
    raw = path.read_text(encoding="utf-8")
    assert "blobref:" in raw
    assert base64.b64encode(payload).decode("ascii") not in raw
    blobs = list((tmp_path / "blobs").iterdir())
    assert len(blobs) == 1 and blobs[0].read_bytes() == payload

    # In memory: original data URL preserved
    history = list(ctx.history)
    part = history[0].content[1]
    assert isinstance(part, ImageURLPart)
    assert part.image_url.url == original_url

    # Restore: rehydrated back to the original data URL
    ctx2 = Context(file_backend=path)
    assert await ctx2.restore()
    part2 = ctx2.history[0].content[1]
    assert isinstance(part2, ImageURLPart)
    assert part2.image_url.url == original_url


@pytest.mark.asyncio
async def test_restore_missing_blob_yields_placeholder(tmp_path: Path) -> None:
    path = tmp_path / "context.jsonl"
    path.touch()
    ctx = Context(file_backend=path)
    await ctx.append_message(_big_image_message(b"\x89PNG" + b"w" * 5000))

    # Delete the blob, then restore
    for blob in (tmp_path / "blobs").iterdir():
        blob.unlink()
    ctx2 = Context(file_backend=path)
    assert await ctx2.restore()
    part = ctx2.history[0].content[1]
    assert isinstance(part, TextPart)
    assert "unavailable" in part.text


@pytest.mark.asyncio
async def test_revert_preserves_blobrefs(tmp_path: Path) -> None:
    path = tmp_path / "context.jsonl"
    path.touch()
    ctx = Context(file_backend=path)

    payload = b"\x89PNG" + b"v" * 5000
    await ctx.checkpoint(add_user_message=False)
    await ctx.append_message(Message(role="user", content=[TextPart(text="before")]))
    await ctx.append_message(_big_image_message(payload))
    await ctx.checkpoint(add_user_message=False)
    await ctx.append_message(Message(role="user", content=[TextPart(text="after")]))

    await ctx.revert_to(1)

    raw = path.read_text(encoding="utf-8")
    assert "blobref:" in raw
    assert "after" not in raw

    ctx2 = Context(file_backend=path)
    assert await ctx2.restore()
    part = ctx2.history[1].content[1]
    assert isinstance(part, ImageURLPart)
    assert part.image_url.url == _data_url(payload)


# ---------------------------------------------------------------------------
# Fork integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fork_copies_referenced_blobs(monkeypatch, tmp_path: Path) -> None:
    share_dir = tmp_path / "share"
    share_dir.mkdir()
    monkeypatch.setattr("cran_code.share.get_share_dir", lambda: share_dir)
    monkeypatch.setattr("cran_code.metadata.get_share_dir", lambda: share_dir)

    from cran_code.session import Session
    from cran_code.wire.file import WireFileMetadata
    from cran_code.wire.protocol import WIRE_PROTOCOL_VERSION
    from cran_code.wire.types import TurnBegin, TurnEnd
    from cran_code.wire.file import WireMessageRecord

    work_dir = KaosPath.unsafe_from_local_path(tmp_path / "work")
    (tmp_path / "work").mkdir()

    source = await Session.create(work_dir)

    # Minimal wire file (metadata + one turn)
    wire_path = source.dir / "wire.jsonl"
    ts = time.time()
    with wire_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(WireFileMetadata(protocol_version=WIRE_PROTOCOL_VERSION).model_dump(mode="json")) + "\n")
        f.write(json.dumps(WireMessageRecord.from_wire_message(TurnBegin(user_input="hi"), timestamp=ts).model_dump(mode="json")) + "\n")
        f.write(json.dumps(WireMessageRecord.from_wire_message(TurnEnd(), timestamp=ts + 1).model_dump(mode="json")) + "\n")

    # Context with an externalized blob
    ctx = Context(file_backend=source.dir / "context.jsonl")
    payload = b"\x89PNG" + b"f" * 5000
    await ctx.append_message(Message(role="user", content=[TextPart(text="hi")]))
    await ctx.append_message(_big_image_message(payload))

    new_id = await fork_session(
        source_session_dir=source.dir,
        work_dir=work_dir,
        turn_index=None,
        source_title="Blob Session",
    )

    new_session = await Session.find(work_dir, new_id)
    assert new_session is not None

    # Blob copied and context still references it
    new_blobs = list((new_session.dir / "blobs").iterdir())
    assert len(new_blobs) == 1
    assert new_blobs[0].read_bytes() == payload
    assert "blobref:" in (new_session.dir / "context.jsonl").read_text(encoding="utf-8")

    # Restored fork rehydrates the image
    ctx2 = Context(file_backend=new_session.dir / "context.jsonl")
    assert await ctx2.restore()
    part = ctx2.history[1].content[1]
    assert isinstance(part, ImageURLPart)
    assert part.image_url.url == _data_url(payload)
