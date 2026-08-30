"""Agent loop：OpenAI 兼容协议（TokenDance 网关）+ 白名单工具 + 宿主注入的 deploy 回调。"""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

from .prompts import DEFAULT_SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, ToolContext, run_local_tool

MAX_TOOL_ITERATIONS = 12

# deploy 回调：返回 "https://..." 表示成功，其他字符串为错误描述
DeployFn = Callable[[ToolContext], Awaitable[str]]


class ModelCallError(Exception):
    """模型调用失败。recovery_action 来自 TokenDance-Recovery-Action 响应头。"""

    def __init__(self, message: str, recovery_action: str | None = None) -> None:
        super().__init__(message)
        self.recovery_action = recovery_action


@dataclass
class LoopOutcome:
    kind: Literal["done", "needs_input", "failed", "over_steps"]
    messages: list[dict] = field(default_factory=list)
    result: dict | None = None
    question: dict | None = None
    error: str | None = None
    config: dict[str, Any] = field(default_factory=dict)


class AgentLoop:
    """受限 agent loop。模型调用与 deploy 副作用全部经由注入点，loop 本身无 IO 依赖。"""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        app_url: str,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        max_iterations: int = MAX_TOOL_ITERATIONS,
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.app_url = app_url
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.timeout = timeout

    async def _chat(self, messages: list[dict]) -> dict:
        payload: dict = {"model": self.model, "messages": messages, "tools": TOOL_SCHEMAS}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "X-App-URL": self.app_url,
                },
                json=payload,
            )
        if resp.status_code != 200:
            raise ModelCallError(
                f"模型网关返回 HTTP {resp.status_code}",
                recovery_action=resp.headers.get("TokenDance-Recovery-Action"),
            )
        return resp.json()

    async def run(
        self,
        history: list[dict],
        ctx: ToolContext,
        deploy: DeployFn,
    ) -> LoopOutcome:
        """跑一轮任务直到终态。history 不含 system 消息。"""
        messages: list[dict] = [{"role": "system", "content": self.system_prompt}, *history]
        url: str | None = None

        for _ in range(self.max_iterations):
            resp = await self._chat(messages)
            msg = resp["choices"][0]["message"]
            messages.append(msg)

            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                messages.append({
                    "role": "user",
                    "content": "请使用工具完成部署（deploy/finish/ask_user/fail 之一）。",
                })
                continue

            for call in tool_calls:
                name = call["function"]["name"]
                try:
                    args = json.loads(call["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = run_local_tool(ctx, name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": result,
                })

            # deploy 是唯一副作用出口：由宿主的 deploy 回调真正执行
            if ctx.deploy_requested:
                ctx.deploy_requested = False
                deploy_result = await deploy(ctx)
                if deploy_result.startswith("https://"):
                    url = deploy_result
                    messages.append({
                        "role": "user",
                        "content": f"deploy 工具结果：部署成功，URL={url}。请调用 finish 总结。",
                    })
                else:
                    messages.append({"role": "user", "content": f"deploy 工具结果：{deploy_result}"})
                continue

            if ctx.question:
                return LoopOutcome(
                    kind="needs_input", messages=messages[1:], question=ctx.question,
                    config=ctx.config,
                )

            if ctx.fail_reason:
                return LoopOutcome(
                    kind="failed", messages=messages[1:], error=ctx.fail_reason,
                    config=ctx.config,
                )

            if ctx.finish_summary:
                if not url:
                    messages.append({"role": "user", "content": "你还没有成功 deploy，不能 finish。"})
                    ctx.finish_summary = None
                    continue
                return LoopOutcome(
                    kind="done", messages=messages[1:],
                    result={"url": url, "summary": ctx.finish_summary},
                    config=ctx.config,
                )

        return LoopOutcome(kind="over_steps", messages=messages[1:], error="任务超过最大处理步数")
