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


class TestReplayDeltaCoalescing:
    """Streaming deltas (98%+ of wire records) must be merged at replay time."""

    def _delta_run(self) -> list[str]:
        records = []
        for chunk in ["{\"", "command", "\": ", "\"ls -la\"", "}"]:
            records.append(
                _record({"type": "ToolCallPart", "payload": {"arguments_part": chunk}})
            )
        return records

    def test_tool_call_parts_merged(self, tmp_path: Path) -> None:
        wire = _write(tmp_path / "wire.jsonl", self._delta_run())
        events = _events(wire)
        assert len(events) == 1
        args = events[0]["params"]["payload"]["arguments_part"]
        assert args == '{"command": "ls -la"}'

    def test_text_parts_merged(self, tmp_path: Path) -> None:
        records = [
            _record({"type": "ContentPart", "payload": {"type": "text", "text": "Hello, "}}),
            _record({"type": "ContentPart", "payload": {"type": "text", "text": "world!"}}),
        ]
        wire = _write(tmp_path / "wire.jsonl", records)
        events = _events(wire)
        assert len(events) == 1
        assert events[0]["params"]["payload"]["text"] == "Hello, world!"

    def test_different_part_types_not_merged(self, tmp_path: Path) -> None:
        records = [
            _record({"type": "ContentPart", "payload": {"type": "think", "think": "hmm…"}}),
            _record({"type": "ContentPart", "payload": {"type": "text", "text": "answer"}}),
        ]
        wire = _write(tmp_path / "wire.jsonl", records)
        assert len(_events(wire)) == 2

    def test_think_parts_merged_unless_encrypted(self, tmp_path: Path) -> None:
        records = [
            _record({"type": "ContentPart", "payload": {"type": "think", "think": "a"}}),
            _record({"type": "ContentPart", "payload": {"type": "think", "think": "b"}}),
            _record(
                {
                    "type": "ContentPart",
                    "payload": {"type": "think", "think": "c", "encrypted": "sig"},
                }
            ),
        ]
        wire = _write(tmp_path / "wire.jsonl", records)
        events = _events(wire)
        assert len(events) == 2
        assert events[0]["params"]["payload"]["think"] == "ab"
        assert events[1]["params"]["payload"]["think"] == "c"

    def test_merge_respects_event_boundaries(self, tmp_path: Path) -> None:
        records = self._delta_run()
        records.append(_record(_turn_text("next turn")))
        records.extend(self._delta_run())
        wire = _write(tmp_path / "wire.jsonl", records)
        events = _events(wire)
        assert len(events) == 3
        assert events[1]["params"]["payload"]["user_input"] == "next turn"


class TestHistoryPagination:
    """Paginated replay: newest page first, older pages via cursor."""

    def _wire_with_turns(self, tmp_path: Path, n: int) -> Path:
        records = [_record(_turn_text(f"turn {i}")) for i in range(n)]
        return _write(tmp_path / "wire.jsonl", records)

    def test_newest_page_returns_tail(self, tmp_path: Path) -> None:
        from cran_code.web.api.sessions import _history_page

        wire_dir = self._wire_with_turns(tmp_path, 10).parent
        page = _history_page(wire_dir, before_line=None, limit=4)
        assert page is not None
        assert len(page.events) == 4
        assert "turn 9" in page.events[-1]
        assert page.has_more is True
        assert page.oldest_line > 0

    def test_older_page_via_cursor(self, tmp_path: Path) -> None:
        from cran_code.web.api.sessions import _history_page

        wire_dir = self._wire_with_turns(tmp_path, 10).parent
        first = _history_page(wire_dir, before_line=None, limit=4)
        assert first is not None
        older = _history_page(wire_dir, before_line=first.oldest_line, limit=4)
        assert older is not None
        assert "turn 5" in older.events[-1]
        oldest = _history_page(wire_dir, before_line=older.oldest_line, limit=4)
        assert oldest is not None
        assert len(oldest.events) == 2
        assert oldest.has_more is False
        assert oldest.oldest_line == 0

    def test_small_file_single_page(self, tmp_path: Path) -> None:
        from cran_code.web.api.sessions import _history_page

        wire_dir = self._wire_with_turns(tmp_path, 3).parent
        page = _history_page(wire_dir, before_line=None, limit=3000)
        assert page is not None
        assert len(page.events) == 3
        assert page.has_more is False

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        from cran_code.web.api.sessions import _history_page

        assert _history_page(tmp_path) is None

    def test_index_cache_reused(self, tmp_path: Path) -> None:
        from cran_code.web.api.sessions import _wire_index, _wire_index_cache

        wire = self._wire_with_turns(tmp_path, 5)
        _wire_index(wire)
        key = str(wire)
        assert key in _wire_index_cache
        first = _wire_index_cache[key]
        _wire_index(wire)
        assert _wire_index_cache[key] is first  # same entry, not rebuilt
