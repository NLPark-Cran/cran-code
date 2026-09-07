# wire/ — 协议层

## 模式

- **事件即契约**：新事件 = `types.py` 加 pydantic 模型 + 加入 `Event` union + `__all__`。Envelope 按类名自动注册（`_NAME_TO_WIRE_MESSAGE_TYPE`），无需其它注册。
- 兼容性：旧事件改名用 `_NAME_TO_WIRE_MESSAGE_TYPE` 别名（参考 `ApprovalRequestResolved`）；字段兼容用 `model_validator(mode="before")`（参考 `SubagentEvent._compat_legacy_fields`）。
- wire.jsonl 是重放来源：事件结构变更必须向后兼容（前端重放历史会话）。
- shell UI / ACP 对未知事件有 `case _: pass` 兜底，但仍要检查 `ui/shell/visualize/_live_view.py` 与 `acp/session.py` 是否需要感知。
- 媒体内容：wire.jsonl 保持内联（前端重放直接渲染）；context.jsonl 走 blobstore 外置——两者是刻意的不同策略。
