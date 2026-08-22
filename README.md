# Cran Code · 猹询码

> 面向高校教学与团队协作场景的 AI Coding 平台 —— 基于 MoonshotAI/kimi-cli 深度演进的 Web 多用户版本。

**生产环境**: <https://crys.tt2.li> · **团队**: NLPark-Cran（杭州电子科技大学）

Cran Code 把终端 AI agent 变成一个**多人协作的 Web 平台**：团队成员在浏览器里创建会话、驱动 agent 完成真实工程任务（读写文件、执行命令、部署服务），平台统一管理账号、团队、API Key、配额与审计。

## 核心能力

- **多用户平台**：v2 JWT 账号体系 + 管理员角色；团队/项目/成员管理；会话共享与协作编辑（Yjs）
- **Key 体系与配额**：个人/团队/共享三级 key 解析，内置 `/px/v1` key 代理（签名 `cwk_` 令牌、自动续期），按用户/团队配额与用量计量页
- **Goal 模式**：给会话设一个结构化目标，agent 跨多轮自治推进直至完成/阻塞/暂停，支持 turn/token/时长预算（默认 30 轮安全上限）
- **Swarm 可视化**：子代理（前台/后台）生命周期实时面板 + 后台任务完成通知
- **完整工程工具链**：24 个内置工具（shell/文件/web/子代理/计划模式/后台任务…）、MCP 扩展、skills 体系、hooks
- **长会话可靠性**：上下文压缩（第一人称交接笔记式）、媒体 blob-ref 外置、分页重放 + 流式碎片合并、断连恢复
- **多主题界面**：石墨靛蓝灰 / 朱砂粉金 / 青碧三套主题（浅色+深色），全量中文/English i18n
- **会话治理**：fork/分叉、归档、AI 生成标题、用量统计页、控制台仪表盘

## 架构一览

```
浏览器 ──WS──▶ FastAPI (SessionProcess) ──JSONRPC/stdio──▶ worker (KimiSoul + kosong → LLM provider)
                     │
                     ├─ wire.jsonl（事件日志，重放来源）      ├─ context.jsonl（模型上下文，blob-ref 外置媒体）
                     ├─ goal.json / subagents/ / blobs/     └─ ~/.cran/cran.db（sqlite：用户/团队/key/配额）
```

- 后端：`src/cran_code`（Python 3.14，FastAPI + 每会话独立 worker 子进程）
- 前端：`web/src`（React 19 + Vite 7 + Tailwind 4 + shadcn）
- 上游基线：kimi-cli v1.49.0 / kosong 0.56.0（通过 `git merge upstream/main` 持续同步）

## 快速开始

```bash
# 环境（需要 uv + Node 20+）
uv lock && uv sync
cd web && npm install && cd ..

# 本地开发（不要占用 5496 生产端口）
uv run cran-code web --port 5494          # 后端
cd web && npm run dev                     # 前端（代理到 5494）

# 冒烟
uv run pytest tests/web/ -q               # 后端 web 层全绿
cd web && npx tsc -b --noEmit             # 前端类型 0 错误
```

## 文档

| 文档 | 内容 |
|---|---|
| [AGENTS.md](AGENTS.md) | AI agent/开发者总纲（第一入口） |
| [docs/dev/architecture.md](docs/dev/architecture.md) | 架构与数据流、安全基线 |
| [docs/dev/conventions.md](docs/dev/conventions.md) | 开发规范（命名/测试/提交/模式库） |
| [docs/dev/deploy.md](docs/dev/deploy.md) | 部署 SOP（验证清单与回滚） |
| [docs/dev/troubleshooting.md](docs/dev/troubleshooting.md) | 故障索引（症状→根因→修复） |
| [docs/dev/goal-mode.md](docs/dev/goal-mode.md) | Goal 模式设计 |
| [docs/dev/changelog.md](docs/dev/changelog.md) | 里程碑归档 |

`docs/en|zh/` 为上游 kimi-cli 用户文档存档（VitePress），其中 `KIMI_*` 环境变量等内容对应上游 CLI，本平台以 `CRAN_*` 为准（见 conventions.md 配置清单）。

## 安全

- v2 管理端点强制 `require_admin`；SSRF 检查；worker 环境只经 `_build_worker_env` 注入；key 代理仅 loopback；敏感路径禁读写
- 密钥永不入库（`~/.cran/config.toml`、`server.env`、`sk-*`）
- 安全研究请见 [SECURITY.md](SECURITY.md)

## 致谢

基于 [MoonshotAI/kimi-cli](https://github.com/MoonshotAI/kimi-cli)（Apache-2.0）演进；持续跟踪上游与 [kimi-code](https://github.com/MoonshotAI/kimi-code) 的能力（Goal 模式等为其设计的移植实现）。
