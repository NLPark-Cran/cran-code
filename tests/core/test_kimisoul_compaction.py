from __future__ import annotations

from pathlib import Path

import pytest
from kosong import StepResult
from kosong.chat_provider import ChatProviderError
from kosong.message import Message
from kosong.tooling.empty import EmptyToolset

import cran_code.soul.compaction as compaction_module
import cran_code.soul.kimisoul as kimisoul_module
from cran_code.soul.agent import Agent, Runtime
from cran_code.soul.context import Context
from cran_code.soul.kimisoul import KimiSoul
from cran_code.wire.types import TextPart


async def _noop() -> None:
    pass


def _make_soul(runtime: Runtime, tmp_path: Path) -> KimiSoul:
    agent = Agent(
        name="Compaction Test Agent",
        system_prompt="Test system prompt.",
        toolset=EmptyToolset(),
        runtime=runtime,
    )
    return KimiSoul(agent, context=Context(file_backend=tmp_path / "history.jsonl"))


def _history_with_huge_tail() -> list[Message]:
    """Build a history where the most recent messages are massive."""
    return [
        Message(role="user", content=[TextPart(text="Old small question")]),
        Message(role="assistant", content=[TextPart(text="Old small answer")]),
        # 100k characters -> ~25k tokens each; together they dominate the context.
        Message(role="user", content=[TextPart(text="x" * 100_000)]),
        Message(role="assistant", content=[TextPart(text="y" * 100_000)]),
    ]


def _short_summary() -> Message:
    return Message(role="assistant", content=[TextPart(text="Short summary.")])


@pytest.mark.asyncio
async def test_compact_context_caps_preserved_tail(
    runtime: Runtime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When recent messages are too large, compaction must not preserve them as-is."""
    soul = _make_soul(runtime, tmp_path)
    for msg in _history_with_huge_tail():
        await soul.context.append_message(msg)
    await soul.context.update_token_count(soul.context.token_count_with_pending)

    step_calls = 0

    async def fake_kosong_step(chat_provider, system_prompt, toolset, history, **kwargs):
        nonlocal step_calls
        step_calls += 1
        return StepResult(
            id="cmp-1",
            message=_short_summary(),
            usage=None,
            tool_calls=[],
            _tool_result_futures={},
        )

    monkeypatch.setattr(compaction_module.kosong, "step", fake_kosong_step)
    monkeypatch.setattr(kimisoul_module, "wire_send", lambda _msg: None)
    monkeypatch.setattr(soul, "_notify_injection_providers_compacted", _noop)

    before = soul.context.token_count
    assert before > 0

    await soul.compact_context()

    # The huge tail should have been dropped from the preserved messages.
    assert soul.context.token_count < before
    assert soul.context.token_count < 500
    # Only one compaction LLM call should have been needed.
    assert step_calls == 1


@pytest.mark.asyncio
async def test_compact_context_falls_back_when_preserved_tail_still_too_large(
    runtime: Runtime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If capping the tail still leaves the estimate above the safe target, fall back to preserving nothing."""
    soul = _make_soul(runtime, tmp_path)
    # Build ~100k tokens of context so the main compaction is below 85% of the
    # original but still above the 50k safe target for the default 100k model.
    for msg in [
        Message(role="user", content=[TextPart(text="Old question " * 25_000)]),
        Message(role="assistant", content=[TextPart(text="Old answer " * 25_000)]),
        Message(role="user", content=[TextPart(text="u" * 50_000)]),
        Message(role="assistant", content=[TextPart(text="a" * 50_000)]),
    ]:
        await soul.context.append_message(msg)
    await soul.context.update_token_count(soul.context.token_count_with_pending)

    summaries: list[str] = []

    async def fake_kosong_step(chat_provider, system_prompt, toolset, history, **kwargs):
        # ~45k tokens: small enough to pass the 85% check but large enough that
        # preserving a single 12.5k-token message pushes the estimate over 50k.
        summary = "summary " * 22_500
        summaries.append(summary)
        return StepResult(
            id="cmp",
            message=Message(role="assistant", content=[TextPart(text=summary)]),
            usage=None,
            tool_calls=[],
            _tool_result_futures={},
        )

    monkeypatch.setattr(compaction_module.kosong, "step", fake_kosong_step)
    monkeypatch.setattr(kimisoul_module, "wire_send", lambda _msg: None)
    monkeypatch.setattr(soul, "_notify_injection_providers_compacted", _noop)

    await soul.compact_context()

    # We should have run compaction twice: main attempt + preserve-zero fallback.
    assert len(summaries) == 2
    # Final context must be below the safe target (50k for the default 100k model).
    assert soul.context.token_count <= 50_000


@pytest.mark.asyncio
async def test_compact_context_raises_when_summary_exceeds_safe_target(
    runtime: Runtime, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If even a preserve-zero summary is too large, compaction must fail safely."""
    soul = _make_soul(runtime, tmp_path)
    for msg in _history_with_huge_tail():
        await soul.context.append_message(msg)
    await soul.context.update_token_count(soul.context.token_count_with_pending)

    async def fake_kosong_step(chat_provider, system_prompt, toolset, history, **kwargs):
        # Return a summary so large that it alone exceeds the safe target.
        return StepResult(
            id="cmp",
            message=Message(role="assistant", content=[TextPart(text="huge " * 100_000)]),
            usage=None,
            tool_calls=[],
            _tool_result_futures={},
        )

    monkeypatch.setattr(compaction_module.kosong, "step", fake_kosong_step)
    monkeypatch.setattr(kimisoul_module, "wire_send", lambda _msg: None)

    with pytest.raises(ChatProviderError):
        await soul.compact_context()

    # Original context must be preserved on failure.
    assert len(soul.context.history) == 4
