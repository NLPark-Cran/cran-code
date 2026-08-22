# AGENTS.md — Cran Code（猹询码）开发总纲

> AI agent 与开发者的第一入口。读这一页即可开始工作；深入主题看 `docs/dev/` 分册。

**Cran Code**（猹询码）是面向高校教学与团队协作场景的 AI Coding 平台：MoonshotAI/kimi-cli (Python) 的 fork + 自建 Web 多用户层（团队/项目/协作编辑/key 体系/配额）。

- 生产：`https://crys.tt2.li`（systemd `cran-code.service`，port 5496，Nginx 反代，`--public`）
- 仓库：`https://github.com/NLPark-Cran/cran-code.git`（团队：NLPark-Cran / 杭州电子科技大学）

## 结构树

```
src/cran_code/            # 后端主包
  soul/                   # agent 主循环、compaction、context 持久化
  agents/default/         # 默认 agent 的 system.md（模型行为总纲）
  prompts/compact.md      # 压缩提示词（第一人称交接笔记式）
  tools/                  # 内置工具（shell/file/web/agent/...）
  wire/                   # 前后端 JSONRPC 协议 + 事件类型
  web/
    runner/process.py     # SessionProcess：worker 生命周期/锁/广播/key 注入/闸门
    api/sessions.py       # v1 会话 API + WS + 分页重放（_WireIndex）
    api_v2/               # 协作 API（users/teams/providers/keyproxy/admin/...）
    db/                   # sqlite 模型 + key 解析链 + 配额
    auth_v2/jwt.py        # v2 JWT + require_user/require_admin
  web/static/             # 前端构建产物（gitignored；index.html 需 git add -f）
packages/kosong/          # vendored LLM 抽象层（跟随上游版本）
web/src/                  # React 19 + Vite 7 + Tailwind 4 + shadcn 前端（全量 i18n）
docs/dev/                 # 开发分册（见下）
.kimi/skills/             # 项目级技能（cran-deploy、cran-review）
```

## 文档地图

| 主题 | 文件 |
|---|---|
| 架构与数据流（server/worker/wire/key 体系/重放分页/安全基线） | `docs/dev/architecture.md` |
| 开发规范（命名、测试基线、提交、安全红线、常用命令） | `docs/dev/conventions.md` |
| 部署 SOP（含验证清单与回滚） | `docs/dev/deploy.md` |
| 故障索引（症状→根因→修复，先查这个） | `docs/dev/troubleshooting.md` |
| 里程碑归档 | `docs/dev/changelog.md` |
| Goal 模式设计（移植方案） | `docs/dev/goal-mode.md` |
| docs/ 写作规范（上游归档） | `docs/dev/documentation-style.md` |

## 不可违背约束（摘要）

1. **安全基线不回退**：provider 管理 `require_admin`；SSRF 检查；worker env 只经 `_build_worker_env`；`/px` 仅 loopback；fs 敏感路径禁读写。详见 architecture.md 末节。
2. **密钥永不入库**（`~/.cran/config.toml`、`server.env`、`sk-*`）。
3. 主包名 `cran_code`，版本号跟随上游（现 1.49.0 / kosong 0.56.0）。
4. 测试纪律：`tests/web` 全绿；`tests/core` 不得超出已知基线失败（清单见 conventions.md）；前端 tsc/vitest/biome 不新增错误；新文案双语。
5. git mutation（commit/push/rewrite）需用户确认。
6. 改动结构/流程/规范时，同步更新对应分册与本文件。

## 当前状态（2026-08-18）

- 最新部署 bundle：`index-DlEgMa01.js`（后端与前端均已上线）。
- 上游同步：已与 MoonshotAI/kimi-cli main 齐平（merge commit 250ad162 之后无 behind）。
- 本轮里程碑全部完成并上线：媒体 blob-ref 外置、swarm 可视化、Goal 模式（P1+P2，设计见 docs/dev/goal-mode.md）、千问办公风视觉收敛。
- 我的 CLI 环境注意：子 agent 与主会话共用同一 Kimi 订阅配额，大批量 agent 工作可能撞上周期上限（403）。

## 快速开始（本地开发）

```bash
uv lock && uv run pytest tests/web/ -q        # 环境 + 后端冒烟
cd web && npm install && npx tsc -b --noEmit  # 前端冒烟
```

本地跑 web 服务：`uv run cran-code web --port 5494`（不要占用 5496 生产端口）。

---

## 团队与产品背景（保留）

**团队成员**：陈镜宇（负责人，全栈/计算语言学）、胡蕴秋（商业分析/项目管理）、郭静俞（产品设计/UIUX）、杨博文（产品运营/调研）等。已验证的落地应用：股猹猹（cha.hub.tt2.li）、EduHelp（py.tt2.li）、月雅湖畔毕业指南（1956.tt2.li）、The Man in Asbestos 课程网站等。
