# 开发规范（conventions）

> 目标：任何 AI agent / 新成员读完后，写出的代码与存量代码"长得像、放得对、测得住"。

## 命名与品牌

- 主包名永远是 `cran_code` / `cran-code`；上游合并或移植社区 PR 时，逐文件把 `kimi_cli.*` 改为 `cran_code.*`、`kimi-cli` 包名引用改掉（`pyproject.toml`、`uv.lock`、wrapper 包 `packages/kimi-code` 依赖 `cran-code==<version>`）。
- 版本号跟随上游 kimi-cli（当前 1.49.0 / kosong 0.56.0）。
- 品牌：「猹询码 Cran Code」。注意：**HTTP header 必须 ASCII**（latin-1），中文品牌名不能进 header。
- 环境变量前缀 `CRAN_*`（上游 `KIMI_*` 仅存于 docs/en|zh 用户文档归档，新代码不用）。

## 代码风格（后端）

- ruff：line-length 100，规则集 E/F/UP/B/SIM/I；提交前 `uv run ruff check <改动文件>` 必须干净。
- pyright：strict 仅对 `src/cran_code/**/*.py` 生效（2026-08-23 修正了指向 `src/kimi_cli` 的陈旧配置）；改动文件 `uv run pyright <files>` 不得新增错误（存量：`web/runner/process.py` 有 2 个）。
- 风格跟随上下文：模块 docstring 说明职责；公共函数写 docstring（Args/Returns/Raises）；类型注解齐全；`from __future__ import annotations` 开头（**例外**：工具类 `__init__.py` 不能加——KimiToolset 依赖注入读取原始注解，字符串化会炸，见 `tools/goal/__init__.py` 注释）。
- 日志用 loguru `cran_code.utils.logging.logger`，结构化 kv（`logger.info("msg {x}", x=x)`）。
- 异步 IO：文件读写用 aiofiles / `asyncio.to_thread` 包裹同步重活（参考 `Context.append_message`）。
- JSON 原子写：`cran_code.utils.io.atomic_json_write`。

## 结构规范（后端：新代码放哪里）

| 要加的东西 | 放哪里 | 范例 |
|---|---|---|
| agent 主循环行为 | `soul/kimisoul.py`（谨慎，先读现有机制） | — |
| 持久化运行时状态（会话级） | `soul/<feature>.py` + `<session_dir>/<feature>.json`（原子写） | `soul/goal.py` |
| 内置工具 | `tools/<group>/__init__.py` + `<name>.md` 描述文件；注册进 `agents/default/agent.yaml` | `tools/goal/` |
| wire 事件 | `wire/types.py`：pydantic 模型 + `Event` union + `__all__`（envelope 按类名自动注册） | `SubagentStatus` |
| v1 会话端点 | `web/api/sessions.py` | `/goal`、`/subagents` |
| v2 平台端点 | `web/api_v2/<domain>.py`，默认 `require_user`，管理动作 `require_admin` | `teams.py` |
| 周期/后台任务 | `background/`（TaskManager 体系） | `agent_runner.py` |

模式约定：

- **wire 事件发射**：agent 循环内用 `get_wire_or_none()` + try/except 静默降级（参考 `subagents/store.py::_emit_status_update`）；shell UI/ACP 对未知事件有 `case _: pass` 兜底，新增事件不会炸旧端。
- **文件即 IPC**：web 主进程与 worker 之间共享会话级状态时，优先读写会话目录里的 JSON 文件（goal.json 模式），worker 在 turn 边界重读——不要发明新的进程间通道。
- **root-only 工具**：`runtime.role != "root"` 直接返回 ToolError；条件可见性用 `KimiToolset.hide()/unhide()`（参考 `soul/goal.py::sync_goal_tool_visibility`）。
- **鉴权三件套**（v1 端点）：`get_session_or_404` → `can_access_session(state, user, await get_user_team_ids(user))` → 业务。范例：`/subagents`、`/goal` 端点。

## 结构规范（前端）

- 页面放 `web/src/pages/`，功能域放 `web/src/features/<domain>/components/`，共享 UI 用 `components/ui/`（shadcn）与 `components/ai-elements/`。
- 全局状态：zustand store 放 `web/src/stores/<name>.ts`（参考 `swarm.ts`/`goal.ts`：Record 键控 + hydrate/clear + 竞态安全合并）。
- wire 事件类型：`hooks/wireTypes.ts` 加类型 + `WireEvent` union；reducer 在 `hooks/useSessionStream.ts` 加 `case`；重放路径自动生效。
- API 调用：用现有 `getApiBaseUrl()` + `getAuthHeader()`；404/403/网络错误优雅降级。
- **所有用户可见字符串进 i18n**：`web/src/i18n/{zh,en}/<ns>.ts` 双语同步（parity 测试强制）；复数用 `_one/_other`（zh 两个形式写同一文案）。
- 主题：颜色只许用 design token（`bg-primary`/`text-muted-foreground`/…），禁止硬编码色值；新主题在主题注册表加一族 token 覆盖（见 index.css）。

## 测试

- 日常验证：`uv run pytest tests/web/ -q`（必须全绿）。
- 核心改动：`uv run pytest tests/core/ -q`。**已知基线失败**（品牌/路径敏感的 inline-snapshot，非回归）：`test_skill.py`(20)、`test_skills_prompt`(2)、`test_load_agents_md`(2)、`test_default_agent`(2F+2E)、`test_agent_spec`(2F+2E)、`test_wire_message`(1F+1E)、`test_plugin_manager`(1F)、`tests/tools/test_tool_schemas`(1F+1E)。合计 30F+5E（tests/core）+ 1F+1E（tests/tools）。
- **已知挂起**：`tests/acp/test_protocol_v1.py`（存量问题，跑全量时排除 tests/acp）。
- kosong 快照测试需要 `respx`（本环境未装），跳过 `packages/kosong/tests/api_snapshot_tests`。
- 前端：`npx tsc -b --noEmit` 必须 0 错误；`npx vitest run` 全过；`npx biome check` 不超过基线（81 个存量错误，逐文件对比不得新增）。
- 新后端逻辑必须带 pytest；测试放对应域目录（`tests/core|web|tools|...`）。
- HTTP 端点测试范式：见 `tests/web/test_session_goal_api.py`（isolated_share_dir fixture + TestClient 上下文管理器跑 lifespan + Bearer session_token + owner_id 设为 v1_anonymous）。
- 路径安全测试必须用 `raw_path` 构造请求（httpx 会规范化 `//`/`%2e`），范例 `tests/web/test_security_regressions.py`。

## 提交

- 分阶段、原子化 commit；commit message 用英文、conventional 前缀（feat/fix/docs/chore），正文可中英文。
- **绝不提交密钥**：`~/.cran/config.toml`、`server.env`、任何 `sk-*` 令牌只在服务器本地。
- `src/cran_code/web/static/` 被 gitignore；部署产物只有 `index.html` 需要 `git add -f`。
- git 历史改写/强推/分支删除需要用户明确批准。

## 安全红线（改动不得削弱）

1. v2 管理端点必须 `require_admin`；新增 v2 端点默认 `require_user`。
2. 任何用户输入的 URL 做服务端请求前必须过 SSRF 检查（https、非内网、禁重定向跟随）。
3. worker 子进程环境只经 `_build_worker_env`。
4. 数据库新表走 `db/models.py` + `create_all`（自动建表）；已有表加列需手工迁移（无 alembic）。
5. 前端凡是用户可见的新字符串进 i18n 词表（`web/src/i18n/{zh,en}/<ns>.ts`）。
6. 文件服务/写入端点必须 `resolve()` + `is_relative_to()` 防遍历与符号链接逃逸；鉴权相关路径判定基于解码后的 ASGI path（2026-08-23 审计结论见 troubleshooting.md）。
7. SPA 兜底不得吞掉任何规范化后属于 `/api/` 的路径（404 必须真 404）。

## 配置清单（CRAN_* 环境变量，18 个）

`CRAN_API_KEY` / `CRAN_BASE_URL` / `CRAN_MODEL_NAME` / `CRAN_MODEL_THINKING_EFFORT`（模型接入）；`CRAN_SHARE_DIR`（默认 `~/.cran`）；`CRAN_DATABASE_URL` / `CRAN_JWT_SECRET` / `CRAN_PROJECT_ROOT`（平台）；`CRAN_KEY_PROXY_PORT` / `CRAN_MAX_FILE_SIZE`；`CRAN_WEB_*`（SESSION_TOKEN/ALLOWED_ORIGINS/ENFORCE_ORIGIN/LAN_ONLY/RESTRICT_SENSITIVE_APIS/MAX_PUBLIC_PATH_DEPTH）；`CRAN_BUILD_SHA` / `CRAN_DISABLE_TELEMETRY`。

## 常用命令

```bash
uv run pytest tests/web/ -q          # 后端 web 层
uv run pytest tests/core/ -q         # 核心（见基线失败清单）
uv run pyright <files>               # 类型检查
uv run ruff check <files>            # lint
cd web && npx tsc -b --noEmit        # 前端类型
cd web && npx vitest run             # 前端单测（i18n parity）
cd web && npx biome check            # 前端 lint（对比基线）
```
