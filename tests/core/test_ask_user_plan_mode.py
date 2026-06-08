"""Tests for AskUserQuestion description stability under plan mode."""

from __future__ import annotations

from pathlib import Path

from cran_code.soul.agent import Agent, Runtime
from cran_code.soul.context import Context
from cran_code.soul.kimisoul import KimiSoul
from cran_code.soul.toolset import KimiToolset
from cran_code.tools.ask_user import _BASE_DESCRIPTION, AskUserQuestion


class TestAskUserDescriptionStability:
    def test_description_stays_static_when_soul_toggles_plan_mode(
        self, runtime: Runtime, tmp_path: Path
    ) -> None:
        """KimiSoul plan mode toggles must not alter AskUserQuestion's description."""
        toolset = KimiToolset()
        tool = AskUserQuestion()
        toolset.add(tool)

        agent = Agent(
            name="Test Agent",
            system_prompt="Test system prompt.",
            toolset=toolset,
            runtime=runtime,
        )
        soul = KimiSoul(agent, context=Context(file_backend=tmp_path / "history.jsonl"))

        before = tool.base.description
        soul._set_plan_mode(True, source="tool")
        during = tool.base.description
        soul._set_plan_mode(False, source="tool")
        after = tool.base.description

        assert before == _BASE_DESCRIPTION
        assert during == _BASE_DESCRIPTION
        assert after == _BASE_DESCRIPTION
