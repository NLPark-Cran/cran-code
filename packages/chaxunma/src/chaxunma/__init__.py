"""chaxunma — 猹询码：cran-code lite 服务端受限 Agent 运行时。

设计哲学借鉴 EVA（usepr/eva）的「单文件受限工具即权限边界」与
kimi-code 的结构清晰度：agent loop 不感知数据库、队列、HTTP——
这些 IO 由宿主（tt2-api）通过依赖注入提供。

典型用法::

    from chaxunma import AgentLoop, ToolContext

    ctx = ToolContext(staging=Path("/srv/tt2/staging/t_xxx"))
    loop = AgentLoop(api_key="sk-...", model="glm-5.3-flash",
                     base_url="https://tokendance.space/gateway/v1",
                     app_url="https://free.hub.tt2.li")
    outcome = await loop.run(messages, ctx)
"""

from .loop import AgentLoop, LoopOutcome, ModelCallError
from .prompts import DEFAULT_SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, ToolContext, run_local_tool

__all__ = [
    "DEFAULT_SYSTEM_PROMPT",
    "AgentLoop",
    "LoopOutcome",
    "ModelCallError",
    "TOOL_SCHEMAS",
    "ToolContext",
    "run_local_tool",
]
