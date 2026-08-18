# 开发规范（conventions）

## 命名与品牌

- 主包名永远是 `cran_code` / `cran-code`；上游合并或移植社区 PR 时，逐文件把 `kimi_cli.*` 改为 `cran_code.*`、`kimi-cli` 包名引用改掉（`pyproject.toml`、`uv.lock`、wrapper 包 `packages/kimi-code` 依赖 `cran-code==<version>`）。
- 版本号跟随上游 kimi-cli（当前 1.49.0 / kosong 0.56.0）。
- 品牌：「猹询码 Cran Code」。注意：**HTTP header 必须 ASCII**（latin-1），中文品牌名不能进 header。

## 测试

- 日常验证：`uv run pytest tests/web/ -q`（必须全绿）。
- 核心改动：`uv run pytest tests/core/ -q`。**已知基线失败**（品牌/路径敏感，非回归）：`test_skill.py`(20)、`test_skills_prompt`(2)、`test_load_agents_md`(2)、`test_default_agent`(2F+2E)、`test_agent_spec`(2F+2E)、`test_wire_message`(1F+1E)、`test_plugin_manager`(1F)、`tests/tools/test_tool_schemas`(1F+1E)。合计 30F+5E（tests/core）+ 1F+1E（tests/tools）。
- **已知挂起**：`tests/acp/test_protocol_v1.py`（存量问题，跑全量时排除 tests/acp）。
- kosong 快照测试需要 `respx`（本环境未装），跳过 `packages/kosong/tests/api_snapshot_tests`。
- 前端：`npx tsc -b --noEmit` 必须 0 错误；`npx vitest run`（i18n parity 等）全过；`npx biome check` 不超过基线（当前 81-83 个存量错误，逐文件对比不得新增）。
- 新后端逻辑必须带 pytest；新前端文案必须双语（zh/en 词表，parity 测试会强制）。

## 提交

- 分阶段、原子化 commit；commit message 用英文、conventional 前缀（feat/fix/docs/chore），正文可中英文。
- **绝不提交密钥**：`~/.cran/config.toml`、`server.env`、任何 `sk-*` 令牌只在服务器本地。
- `src/cran_code/web/static/` 被 gitignore；部署产物只有 `index.html` 需要 `git add -f`。
- git 历史改写/强推需要用户明确批准。

## 安全红线（改动不得削弱）

1. v2 管理端点必须 `require_admin`；新增 v2 端点默认 `require_user`。
2. 任何用户输入的 URL 做服务端请求前必须过 SSRF 检查（https、非内网、禁重定向跟随）。
3. worker 子进程环境只经 `_build_worker_env`。
4. 数据库新表走 `db/models.py` + `create_all`（自动建表）；已有表加列需手工迁移（无 alembic）。
5. 前端凡是用户可见的新字符串进 i18n 词表（`web/src/i18n/{zh,en}/<ns>.ts`）。

## 常用命令

```bash
uv run pytest tests/web/ -q          # 后端 web 层
uv run pytest tests/core/ -q         # 核心（见基线失败清单）
uv run pyright <files>               # 类型检查（process.py 有 2 个存量错误）
cd web && npx tsc -b --noEmit        # 前端类型
cd web && npx vitest run             # 前端单测（i18n parity）
cd web && npx biome check            # lint（对比基线）
```
