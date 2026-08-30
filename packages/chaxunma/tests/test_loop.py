"""chaxunma loop 单测（脚本化模型响应 + 打桩 httpx）。"""

import json
from pathlib import Path

import pytest

from chaxunma import AgentLoop, ToolContext
from chaxunma.loop import ModelCallError


def _tool_call(call_id: str, name: str, args: dict) -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }


def _msg(*calls: dict) -> dict:
    return {
        "choices": [
            {"message": {"role": "assistant", "content": None, "tool_calls": list(calls)}}
        ]
    }


class ScriptedLoop(AgentLoop):
    """用脚本响应替代真实模型调用。"""

    def __init__(self, script: list[dict]) -> None:
        super().__init__(
            api_key="sk-test",
            model="glm-5.3-flash",
            base_url="https://example.invalid",
            app_url="https://free.hub.tt2.li",
        )
        self.script = script
        self.n = 0

    async def _chat(self, messages: list[dict]) -> dict:
        resp = self.script[min(self.n, len(self.script) - 1)]
        self.n += 1
        return resp


async def _deploy_ok(ctx: ToolContext) -> str:
    return "https://demo.lhub.tt2.li"


async def _deploy_taken(ctx: ToolContext) -> str:
    return "错误：name_taken"


@pytest.fixture
def ctx(tmp_path: Path) -> ToolContext:
    (tmp_path / "index.html").write_text("<html>hi</html>")
    return ToolContext(tmp_path)


class TestDone:
    async def test_happy_path(self, ctx):
        loop = ScriptedLoop([
            _msg(_tool_call("1", "list_files", {})),
            _msg(_tool_call("2", "decide_config", {"spa": False})),
            _msg(_tool_call("3", "deploy", {})),
            _msg(_tool_call("4", "finish", {"summary": "ok"})),
        ])
        outcome = await loop.run([{"role": "user", "content": "deploy"}], ctx, _deploy_ok)
        assert outcome.kind == "done"
        assert outcome.result and outcome.result["url"] == "https://demo.lhub.tt2.li"


class TestNeedsInput:
    async def test_ask_user(self, ctx):
        loop = ScriptedLoop([_msg(_tool_call("1", "ask_user", {"question": "SPA?"}))])
        outcome = await loop.run([{"role": "user", "content": "deploy"}], ctx, _deploy_ok)
        assert outcome.kind == "needs_input"
        assert outcome.question and outcome.question["question"] == "SPA?"


class TestDeployRetry:
    async def test_name_taken_then_ask(self, ctx):
        loop = ScriptedLoop([
            _msg(_tool_call("1", "deploy", {})),
            _msg(_tool_call("2", "ask_user", {"question": "换个名字？"})),
        ])
        outcome = await loop.run([{"role": "user", "content": "deploy"}], ctx, _deploy_taken)
        assert outcome.kind == "needs_input"


class TestFail:
    async def test_fail(self, ctx):
        loop = ScriptedLoop([_msg(_tool_call("1", "fail", {"reason": "违规"}))])
        outcome = await loop.run([{"role": "user", "content": "x"}], ctx, _deploy_ok)
        assert outcome.kind == "failed" and outcome.error == "违规"

    async def test_over_steps(self, ctx):
        loop = ScriptedLoop([_msg(_tool_call("1", "list_files", {}))])
        outcome = await loop.run([{"role": "user", "content": "x"}], ctx, _deploy_ok)
        assert outcome.kind == "over_steps"


class TestModelError:
    async def test_recovery_action(self, ctx, monkeypatch):
        import httpx

        class FakeResp:
            status_code = 402
            headers = {"TokenDance-Recovery-Action": "top_up_balance"}

            def json(self):
                return {}

        class FakeClient:
            def __init__(self, **kw): ...

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, *a, **kw):
                return FakeResp()

        monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
        loop = AgentLoop(api_key="sk-x", model="m", base_url="https://x", app_url="https://a")
        with pytest.raises(ModelCallError) as exc:
            await loop.run([], ctx, _deploy_ok)
        assert exc.value.recovery_action == "top_up_balance"
