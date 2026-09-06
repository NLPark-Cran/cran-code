# AGENTS.md — Cran Code（猹询码）开发总纲

> AI agent 与开发者的第一入口。读这一页即可开始工作；深入主题看 `docs/dev/` 分册。
> **本文件是抗 /compact 的记忆锚点**：所有长期约束与当前状态必须写在这里或链接的分册里。

**Cran Code**（猹询码）是面向高校教学与团队协作场景的 AI Coding 平台：MoonshotAI/kimi-cli (Python) 的演进 fork + 自建 Web 多用户层（团队/项目/协作编辑/key 体系/配额/Goal 模式/Swarm 可视化）。

- 生产：`https://crys.tt2.li`（systemd `cran-code.service`，port 5496，Nginx 反代，`--public`）
- 仓库：`https://github.com/NLPark-Cran/cran-code.git`（独立仓库，已脱离 fork 网络；上游同步走本地 `git merge upstream/main`）
- 上游基线：**冻结在 kimi-cli v1.49.0 / kosong 0.56.0**（1.50 已转入 kimi-code 迁移轨道，只挑安全修复 cherry-pick，不再 merge）

## 结构树

```
src/cran_code/            # 后端主包（~60k LOC）
  soul/                   # agent 主循环（kimisoul 2.2k 行）、compaction、context 持久化、
                          # goal.py（Goal 模式）、blobstore.py（媒体外置）
  agents/default/         # 默认 agent 的 system.md + agent.yaml（工具注册表）
  prompts/compact.md      # 压缩提示词（第一人称交接笔记式）
  tools/                  # 24 个内置工具（shell/file/web/agent/goal/background/...）
  wire/                   # 前后端 JSONRPC 协议 + 事件类型（types.py 单一注册表）
  web/
    runner/process.py     # SessionProcess：worker 生命周期/锁/广播/key 注入/闸门（1.4k 行）
    api/sessions.py       # v1 会话 API + WS + 分页重放 + goal/subagents 端点（1.9k 行）
    api_v2/               # 协作 API（users/teams/providers/keyproxy/admin/fs/git/...，55 路由）
    db/                   # sqlite 11 表 + key 解析链 + 配额
    auth_v2/jwt.py        # v2 JWT + require_user/require_admin
  web/static/             # 前端构建产物（gitignored；index.html 需 git add -f）
packages/kosong/          # vendored LLM 抽象层（跟随上游 0.56.0）
web/src/                  # React 19 + Vite 7 + Tailwind 4 + shadcn（197 文件，i18n 12 ns × 2 语言）
docs/dev/                 # 开发分册（见下）
.kimi/skills/             # 项目级技能（cran-deploy、cran-review）
```

## 文档地图

| 主题 | 文件 |
|---|---|
| 架构与数据流（server/worker/wire/key 体系/重放分页/安全基线） | `docs/dev/architecture.md` |
| 开发规范（命名、结构、模式库、测试基线、提交、安全红线、配置清单） | `docs/dev/conventions.md` |
| 部署 SOP（含验证清单与回滚） | `docs/dev/deploy.md` |
| 故障索引（症状→根因→修复，先查这个） | `docs/dev/troubleshooting.md` |
| Goal 模式设计（移植自 kimi-code GOAL.md） | `docs/dev/goal-mode.md` |
| 里程碑归档 | `docs/dev/changelog.md` |
| docs/ 写作规范（上游归档） | `docs/dev/documentation-style.md` |

## 不可违背约束（摘要）

1. **安全基线不回退**：provider 管理 `require_admin`；SSRF 检查；worker env 只经 `_build_worker_env`；`/px` 仅 loopback；fs 敏感路径禁读写；文件端点 `resolve()+is_relative_to` 强制。详见 architecture.md 末节与 troubleshooting.md 安全节。
2. **密钥永不入库**（`~/.cran/config.toml`、`server.env`、`sk-*`）。
3. 主包名 `cran_code`，版本号跟随上游（现 1.49.0 / kosong 0.56.0）。
4. 测试纪律：`tests/web` 全绿；`tests/core` 不得超出已知基线（30F+5E，清单见 conventions.md）；前端 tsc 0 错 + vitest 全绿 + biome 不新增；新文案双语（zh/en，parity 测试强制）。
5. git mutation（commit/push/rewrite/分支删除）需用户确认。
6. 改动结构/流程/规范时，同步更新对应分册与本文件。

## 当前状态（2026-08-23）

- 最新部署 bundle：`index-CHTQ-PFh.js`（后端与前端均已上线）。
- 已上线大特性：Goal 模式（P1+P2）、Swarm 可视化、媒体 blob-ref、千问办公风 v1（紫色，将被多主题系统取代）。
- 已完成并上线：媒体 blob-ref 外置、swarm 可视化、Goal 模式（P1+P2）、多主题系统（石墨/朱砂粉金/青碧）、read-before-write、时区化用量统计、环境模板自动注入、git 自动初始化、机密脱敏。
- 进行中：洛书（github.com/NLPark-Cran/luoshu，ADR 见仓库 docs/）；陪伴记忆（ADR 002）；知识库双轨 KB 侧。
- 仓库卫生：origin 只保留 main（33 个上游镜像分支 + crina 已清理；crina 独有文档已拣入 main）。
- 信任模型：worker 以 root 执行 shell，多用户隔离靠配额/审批/团队边界，非 OS 沙箱（见 troubleshooting.md）。
- 我的 CLI 环境注意：子 agent 与主会话共用同一 Kimi 订阅配额，大批量 agent 工作可能撞上周期上限（403）。

## 快速开始（本地开发）

```bash
uv lock && uv run pytest tests/web/ -q        # 环境 + 后端冒烟
cd web && npm install && npx tsc -b --noEmit  # 前端冒烟
```

本地跑 web 服务：`uv run cran-code web --port 5494`（不要占用 5496 生产端口）。

---

## 团队与产品背景（保留）

**团队成员**：陈镜宇（负责人，全栈/计算语言学）、胡蕴秋（商业分析/项目管理）、郭静俞（产品设计/UIUX）、杨博文（产品运营/调研）等。已验证的落地应用：股猹猹（cha.hub.tt2.li）、EduHelp（py.tt2.li）、月雅湖畔毕业指南（1956.tt2.li）、The Man in Asbestos 课程网站、镜听空间（here.crina.at，集成约定见 `examples/crina-space/`）等。
