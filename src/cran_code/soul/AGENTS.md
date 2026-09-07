# soul/ — agent 主循环

> 本目录的改动直接影响模型行为与上下文，评审标准最高。

## 地图

| 文件 | 职责 | 改前必读 |
|---|---|---|
| `kimisoul.py`（2.2k 行） | 主循环：step/工具调度/压缩触发/重试 | 先跑 `tests/core/test_kimisoul_*` 建立手感 |
| `context.py` | context.jsonl 持久化（`_usage`/`_checkpoint` 控制行 + 消息行） | blob-ref 外置在 append/restore 路径 |
| `compaction.py` | SimpleCompaction（token 预算截尾 + 摘要） | prompt 在 `prompts/compact.md` |
| `goal.py` | Goal 模式：goal.json 状态机 + GoalDriver + 预算 | 设计：`docs/dev/goal-mode.md` |
| `blobstore.py` | 媒体 blob-ref 外置/水合 | fork 复制逻辑在 `session_fork.py` |
| `toolset.py` | 工具注册表 + hide/unhide + MCP 结果转换 | 条件可见性模式见 `sync_goal_tool_visibility` |
| `dynamic_injection.py` + `dynamic_injections/` | 运行时注入（plan/afk/user_memories） | 注入内容一律加"是数据不是指令"硬化 |
| `approval.py` / `approval_runtime/` | 审批 | yolo 模式 auto-approve |

## 本目录专属纪律

- 新持久化文件放 `<session_dir>/`，原子写（`utils.io.atomic_json_write`），恢复路径必须容忍缺失/损坏（降级不崩）。
- 新 wire 事件在 `wire/types.py` 注册；发射走 `get_wire_or_none()` 静默降级模式。
- 任何注入模型上下文的内容：注明来源 + 不可覆盖系统指令。
