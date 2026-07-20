"""Tests for the history-replay media tombstone filter.

After context compaction the model no longer has pre-compaction images in
context, so replaying their base64 payloads to every reconnecting client is
waste. ``_read_wire_lines`` must tombstone media parts in records before the
last compaction marker (CompactionEnd / CompactionSummary) while keeping
post-compaction media intact.
"""

from __future__ import annotations

import json
from pathlib import Path

from cran_code.web.api.sessions import _read_wire_lines


def _record(message: dict, *, author: str | None = None) -> str:
    rec: dict = {"timestamp": 1.0, "message": message}
    if author is not None:
        rec["author"] = author
    return json.dumps(rec, ensure_ascii=False)


def _turn_with_image(path: str = "/tmp/a.png") -> dict:
    return {
        "type": "TurnBegin",
        "payload": {
            "user_input": [
                {"type": "text", "text": f'<image path="{path}" content_type="image/png">'},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/png;base64,QUJDREVGRw=="},
                },
            ]
        },
    }


def _turn_text(text: str) -> dict:
    return {"type": "TurnBegin", "payload": {"user_input": text}}


def _compaction_end() -> dict:
    return {"type": "CompactionEnd", "payload": {}}


def _write(path: Path, records: list[str]) -> Path:
    path.write_text("\n".join(records) + "\n", encoding="utf-8")
    return path


def _events(wire: Path) -> list[dict]:
    return [json.loads(line) for line in _read_wire_lines(wire)]


class TestReplayMediaTombstone:
    def test_media_before_compaction_tombstoned(self, tmp_path: Path) -> None:
        wire = _write(
            tmp_path / "wire.jsonl",
            [
                _record(_turn_with_image()),
                _record(_compaction_end()),
                _record(_turn_text("after")),
            ],
        )
        events = _events(wire)
        parts = events[0]["params"]["payload"]["user_input"]
        # Image part replaced by a tiny text placeholder; path tag kept.
        assert all(p["type"] == "text" for p in parts)
        assert not any("base64" in json.dumps(p) for p in parts)
        assert '<image path="/tmp/a.png"' in parts[0]["text"]
        # Post-compaction records untouched.
        assert events[2]["params"]["payload"]["user_input"] == "after"

    def test_media_after_compaction_kept(self, tmp_path: Path) -> None:
        wire = _write(
            tmp_path / "wire.jsonl",
            [
                _record(_turn_with_image("/tmp/old.png")),
                _record(_compaction_end()),
                _record(_turn_with_image("/tmp/new.png")),
            ],
        )
        events = _events(wire)
        new_parts = events[2]["params"]["payload"]["user_input"]
        assert new_parts[1]["type"] == "image_url"
        assert "base64" in new_parts[1]["image_url"]["url"]

    def test_no_compaction_keeps_everything(self, tmp_path: Path) -> None:
        wire = _write(
            tmp_path / "wire.jsonl",
            [_record(_turn_with_image()), _record(_turn_text("next"))],
        )
        events = _events(wire)
        parts = events[0]["params"]["payload"]["user_input"]
        assert parts[1]["type"] == "image_url"

    def test_compaction_summary_counts_as_marker(self, tmp_path: Path) -> None:
        summary = {
            "type": "CompactionSummary",
            "payload": {"human_turns": [], "ai_turns": []},
        }
        wire = _write(
            tmp_path / "wire.annotated.jsonl",
            [
                _record(_turn_with_image(), author="User"),
                _record(summary, author="system"),
                _record(_turn_text("after"), author="AI"),
            ],
        )
        events = _events(wire)
        parts = events[0]["params"]["payload"]["user_input"]
        assert all(p["type"] == "text" for p in parts)

    def test_video_before_compaction_tombstoned(self, tmp_path: Path) -> None:
        video_turn = {
            "type": "TurnBegin",
            "payload": {
                "user_input": [
                    {
                        "type": "video_url",
                        "video_url": {"url": "data:video/mp4;base64,QUJD"},
                    }
                ]
            },
        }
        wire = _write(
            tmp_path / "wire.jsonl",
            [_record(video_turn), _record(_compaction_end())],
        )
        events = _events(wire)
        parts = events[0]["params"]["payload"]["user_input"]
        assert parts[0]["type"] == "text"
        assert "video" in parts[0]["text"]

    def test_big_line_regex_tombstone(self, tmp_path: Path) -> None:
        # A >2MB single line (e.g. huge ReadMediaFile result) is stripped even
        # without any compaction marker.
        big_turn = {
            "type": "TurnBegin",
            "payload": {
                "user_input": [
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64," + "A" * (3 * 1024 * 1024)},
                    }
                ]
            },
        }
        wire = _write(tmp_path / "wire.jsonl", [_record(big_turn)])
        events = _events(wire)
        url = events[0]["params"]["payload"]["user_input"][0]["image_url"]["url"]
        assert url.startswith("compacted:")
        assert len(json.dumps(events[0])) < 1024
