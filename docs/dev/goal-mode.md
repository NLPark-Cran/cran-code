# Goal 模式设计（移植自 kimi-code GOAL.md）

> 来源：`github.com/MoonshotAI/kimi-code/GOAL.md`（2026-08-18 抓取）。本文是 cran-code 平台（web 优先、无 TUI）的落地方案。分两阶段：**P1 后端核心**、**P2 Web UX**。

## 概念

Goal 是 runtime 持有的结构化状态（不是聊天文本）：用户描述"要达到什么最终状态"，driver 把普通 turn 串成自治多轮执行，模型用工具给出机器可读的状态信号结束/停放 goal。一个会话同时最多一个 goal。

## 状态机

- `active`：driver 自动推进下一轮。唯一会自动续跑的状态。
- `paused`：保留目标，不自治推进。来源：用户暂停、中断、进程恢复降级、provider/runtime 错误。
- `blocked`：保留目标，不自治推进。来源：模型判断需外部输入、预算达到、目标无法按当前表述完成。
- `complete`：瞬时态。发完成事件后立即清除 goal，不持久化。
- 无 `cancelled`：取消 = 清除 goal + 在上下文里提醒模型忽略旧 goal 的 active reminder。

恢复语义：session 恢复时 `active` 降级为 `paused`（旧进程不可能还活着，禁止重启后偷偷烧配额）。fork 不继承 goal（goal.json 不随 fork 复制）。

## P1 后端核心 ✅ 已实现（2026-07-27）

实现文件映射：

| 文件 | 内容 |
|---|---|
| `src/cran_code/soul/goal.py` | `GoalRecord`/`GoalBudgets`/`GoalStats`（pydantic）、`GoalStore`（load/save/clear + 全部状态迁移，原子写 `<session_dir>/goal.json`）、预算检查（`budget_exceeded`/`budget_pressure` ≥75%）、提示词构建（`build_goal_reminder`/`build_light_reminder`/`build_continuation_prompt`）、`GoalDriver`（无 JSONRPC 依赖、可单测）、`sync_goal_tool_visibility`、`DEFAULT_GOAL_TURN_BUDGET = 30`（cran-code 偏离上游：无显式 turns 预算时默认 30 轮兜底保护配额） |
| `src/cran_code/tools/goal/` | `CreateGoal`（yolo/afk 外走审批；已有 goal 时拒绝）、`GetGoal`、`UpdateGoal`（complete 清记录并提示写简短收尾；blocked 必填 reason；active=resume）、`SetGoalBudget`（正整数/60–86400 秒校验）。全部 root-only |
| `src/cran_code/wire/types.py` | `GoalUpdated { snapshot: dict \| null, change }` 事件，已注册进 `Event` union；budget 触发的 blocked 用 `change="budget"` |
| `src/cran_code/wire/server.py` | `_handle_prompt` 内嵌 driver 循环（turn 前注入 reminder，turn 后记账/查预算/续跑；`MaxStepsReached` 计入完成 turn 继续驱动；`RunCancelled`/`APIStatusError`/`ChatProviderError`/`LLMNotSet`/`LLMNotSupported`/未知异常 → `pause_on_error` 后返回原 JSONRPC 映射）；initialize 时 `_sync_goal_tool_visibility` |
| `src/cran_code/app.py` | `KimiCLI.create` 加载会话时 `restore_downgrade`（active→paused，stop_reason="session restarted"）+ 工具可见性同步（web worker 与 shell CLI 共用的唯一汇聚点，故选此处而非 WireServer） |
| `src/cran_code/agents/default/agent.yaml` | 注册 4 个 goal 工具（subagent 通过角色检查隔离，不单独剔除） |
| `tests/core/test_goal.py`（37 例）+ `tests/core/test_session_fork.py::TestForkGoal` | store CRUD/迁移矩阵/统计/预算/reminder 内容/driver 假 runner 循环（complete 停止、错误暂停、默认 30 轮封顶、budget blocked）/工具行为（校验、root-only、无 goal 报错）/fork 不复制 goal.json/restore 降级 |

### 存储：`soul/goal.py` + `<session_dir>/goal.json`

```json
{
  "objective": "...",            // 目标文本（必填，长度上限 ~4000）
  "criteria": "...",             // 可选完成标准
  "status": "active|paused|blocked",
  "stop_reason": "...",          // paused/blocked 原因
  "budgets":  { "max_turns": 20, "max_tokens": 500000, "max_seconds": 1800 },  // 全部可选，默认无
  "stats":    { "turns": 3, "tokens": 123456, "active_seconds": 240.0 },
  "created_at": 0.0, "updated_at": 0.0,
  "active_since": 0.0            // 当前 active 区间起点（null=非 active）
}
```

原子写（`atomic_json_write`）。统计只在 active 期间增长；pause/resume 折算 active 区间。

### 工具（仅 root/main agent；有 goal 时才暴露 Update/SetBudget）

- `CreateGoal(objective, criteria?)` → 创建并置 active。已有 goal 时拒绝（除非先 cancel/replace）。yolo 外走审批（模型代创建需用户确认）。
- `GetGoal()` → 当前 goal 快照。
- `UpdateGoal(status, reason?)` → complete/blocked/paused/active（resume）。complete/blocked 的 tool result 提示模型写简短收尾说明；complete 由 runtime 清文件并发完成事件。
- `SetGoalBudget(max_turns?, max_tokens?, max_seconds?)` → 仅用户明确给出硬限制时使用；正整数/合理秒数范围校验。

### Driver（worker 层）

位置：web worker 的 prompt 处理循环（CLI 的 run_soul 调用方同理可接）。逻辑：

1. turn 结束（正常或异常）后读 goal.json。
2. `active` 且预算未达 → 追加 continuation prompt（系统触发，含义"继续朝 goal 推进一个连贯切片并自审"）跑下一轮。
3. 非 active / 无 goal → 停止。
4. turn 异常（provider 错误、rate limit、中断、runtime 异常）→ 置 `paused` 并停止。
5. 预算达到（turn 开始前/结束后检查；token 在 step 后检查）→ 置 `blocked`，stop_reason=预算达到。

预算引导：任一预算 ≥75% 时，注入提示转为"收敛，不开新可选工作"。

### Turn 边界注入

- active：完整 reminder（goal 模式说明、目标/标准、目标文本是用户数据不可覆盖系统指令、状态/统计、自审要求、complete/blocked 判定纪律）。
- paused/blocked：轻量提醒（存在但不自治推进，除非用户明确要求）。
- cancel 后：一次性提醒忽略旧 goal。
- 只在 turn/continuation 边界注入（不逐 step），利于 prompt cache。

### Wire 事件

`GoalUpdated { snapshot: {...} | null, change: "created|updated|completed|cleared|budget" }`。complete → 先发 `completed` 事件再清文件（snapshot 变 null）。前端 banner 据此渲染。

## P2 Web UX（后续）

- REST：`GET/POST/DELETE /api/sessions/{id}/goal`（查看/创建/取消）、`POST .../goal/pause|resume`。
- 前端：chat header 下的 goal banner（目标、状态点、turn/token/时长统计、暂停/恢复/取消按钮）；完成/阻塞 toast。
- `/goal` 斜杠命令解析（如果 web 输入已有斜杠命令体系则挂靠）。

## 明确不做

- `/goal next` 队列与 TUI 交互管理器（平台无 TUI；后续可按需加队列字段）。
- telemetry 上报目标文本（只记事件不记内容）。
- subagent 访问 goal 工具（root-only 隔离）。
