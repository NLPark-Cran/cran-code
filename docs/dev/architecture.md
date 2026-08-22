# Cran Code 架构（写给开发者与 AI agent）

> 本文是代码结构的权威说明。改动结构时同步更新本文。

## 总览

Cran Code = MoonshotAI/kimi-cli (Python) 的 fork + 自建 Web 多用户层。两条运行路径：

- **CLI/TUI**：`cran` 命令直接使用 `soul`（agent loop）。
- **Web 服务**：`cran-code web`（FastAPI, port 5496）→ 每个会话一个 **worker 子进程**（`python -m cran_code.web.runner.worker <session_id>`），主进程通过 **stdin/stdout JSONRPC**（wire 协议）与 worker 通信，浏览器经 **WebSocket** 收发。

```
浏览器 ──WS──▶ FastAPI (SessionProcess) ──JSONRPC/stdio──▶ worker (KimiSoul + kosong → LLM provider)
                     │
                     ├─ wire.jsonl / wire.annotated.jsonl（事件日志，重放来源）
                     ├─ context.jsonl（模型上下文，compaction 会重建；大媒体以 blobref 外置）
                     ├─ blobs/（context 媒体的内容寻址 blob，随会话目录同生同灭）
                     └─ ~/.cran/cran.db（sqlite：用户/团队/key/配额/用量）
```

## 关键模块

| 模块 | 职责 | 注意点 |
|---|---|---|
| `soul/kimisoul.py` | agent 主循环（step/工具/压缩/重试） | 任何改动先跑 `tests/core/test_kimisoul_*` |
| `soul/compaction.py` | SimpleCompaction + 提示词 | prompt 在 `prompts/compact.md`（第一人称交接笔记式） |
| `soul/context.py` | context.jsonl 持久化（含 `_usage` token 账本、checkpoint） | restore 会读回 `_usage`；append 时大媒体外置为 blobref |
| `soul/blobstore.py` | 媒体 blob-ref：写时把 ≥1KB 的 data: URL 存为 `blobs/<sha256>.<ext>`，restore 时水合回 data URL；blob 缺失降级为文本占位片 | fork 会按引用复制 blob；wire.jsonl 不外置（前端重放需要内联） |
| `web/runner/process.py` | SessionProcess：worker 生命周期、锁、广播、key 注入、prompt 闸门、pending 请求跟踪、initialize 缓存/去重 | `_lock` 保护的临界区，勿在持锁时调 restart |
| `web/api/sessions.py` | v1 会话 API + WS stream + 分页重放（`_WireIndex` 偏移索引缓存） | 重放只发最新一页；更老分页走 HTTP |
| `web/api_v2/` | 协作平台 API（users/teams/projects/providers/keyproxy/admin/fs/git/terminal/collab） | 全部 v2 JWT；管理动作用 `require_admin` |
| `web/api_v2/keyproxy.py` | `/px/v1` key 代理：cwk_ HMAC 令牌（3 天 TTL）、loopback-only、路径白名单、配额 429、用量计量 | 团队/共享 key 的唯一通道 |
| `web/db/keys.py` | key 解析链 personal→team→shared + 配额语义 | 共享配额只统计 source='shared' |
| `web/db/connection.py` | sqlite：NullPool + WAL + busy_timeout | 勿恢复连接池上限（会再次耗尽） |
| `web/auth_v1.py` / `auth_v2/jwt.py` | v1 桥接（含 local 合成用户）/ v2 JWT（30 天） | `is_active` 在多处校验 |
| `packages/kosong/` | LLM 抽象层（vendored 上游包） | 版本号跟随上游；`kimi_cli`→`cran_code` 改写规范见 conventions.md |
| `web/src/` | React 19 + Vite 7 + Tailwind 4 + shadcn 前端 | i18n 全量（zh 默认）；新字符串必须双语 |
| `soul/goal.py` + `tools/goal/` | Goal 模式 P1：goal.json 存储/状态机/预算、`GoalDriver` 多轮自治循环、4 个 root-only 工具 | 无显式 turns 预算时默认 30 轮封顶；恢复时 active→paused 降级在 `KimiCLI.create` |

## Key 体系与流量路径

1. worker 启动时 `_build_worker_env` 注入凭证：
   - personal key → 直接注入（kimi: `CRAN_API_KEY`；openai_*: `OPENAI_API_KEY`）
   - team/shared key → `OPENAI_BASE_URL=http://127.0.0.1:<port>/px/v1` + `OPENAI_API_KEY=cwk_<token>`（worker 永远不见真 key）
2. 代理每请求重新解析 key（吊销即时生效）、校验配额、转发上游、记录 `usage_records`。
3. personal key 的用量由 `process.py` 从 wire `StatusUpdate.token_usage` 记录（两条路径互不重复计数）。
4. prompt 闸门（`_prompt_gate_error`）：无 key/无授权/配额耗尽 → 立即返回可操作的 JSONRPC 错误。

## 重放与分页（性能关键路径）

- WS 连接后只重放**最新一页**（3000 原始行，合并流式碎片后通常几百条）；`history_complete.params` 带 `{has_more_history, oldest_line, turn_base, source}`。
- 更早历史：`GET /api/sessions/{id}/history?before_line=N`（游标式），前端向上滚动时拉取并前插。
- `_read_wire_lines`/`_parse_wire_window` 做三件事：compaction 前媒体 tombstone、>2MB 单行正则剥离、连续流式碎片合并（ContentPart/ToolCallPart）。
- 压缩事件（Begin/Summary/End）会写入 `wire.annotated.jsonl`；重放源优先 annotated（**不含** JSONRPC 请求类——pending 问题靠 `SessionProcess._pending_requests` 补发）。

## 安全基线（不可回退）

- Provider 管理/模型切换/任意 URL 探测 = `require_admin`；fetch-models 复用已存 key 时 base_url 必须精确匹配。
- worker 环境剥离所有 `CRAN_*_SECRET` 与 provider 凭证变量（`_sanitize_worker_env`），只经 `_build_worker_env` 定向注入。
- `/px` 仅 loopback；cwk_ 令牌含 exp；登录/注册限流 10/min/IP（XFF 仅在 loopback 对端可信）。
- fs API 对敏感路径（.env/.git/.ssh/.aws/.cran/.kimi/.config 下的 server.env/config.toml）读写均禁。
- 已知残余风险：worker 与 server 同为 root（完全隔离需非 root worker，已排期）。
