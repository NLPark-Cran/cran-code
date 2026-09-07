# tools/ — 内置工具

## 模式

- 每个工具一个子目录：`<name>/__init__.py`（工具类）+ `<name>.md`（模型可见描述，**改行为必同步改描述**，`tests/tools/test_tool_descriptions.py` 快照守护）。
- 构造依赖注入（Runtime/Approval/KimiToolset…）：**`__init__.py` 禁止 `from __future__ import annotations`**（注入读取原始注解，字符串化会炸）。
- root-only 工具：`runtime.role != "root"` → ToolError（见 `tools/goal/`、`tools/memory/`）。
- 新工具注册进 `agents/default/agent.yaml`；条件可见用 `KimiToolset.hide()/unhide()`。
- 机密处理：工具输出可能含机密时主动脱敏（前端 `lib/redact.ts` 有对应展示层）。

## 现有工具组

shell / file（含 read-before-write 纪律，见 `file/read_tracker.py`）/ web / agent（子代理）/ background（TaskList/TaskOutput/TaskStop）/ goal / memory / plan / ask_user / todo / dmail / minimax_consult
