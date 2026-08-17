# crina-space 集成示例（镜听空间 · here.crina.at）

本目录是「镜听空间」对 cran-code 的集成约定。实际驱动代码住在
[here.crina.at 仓库](https://github.com/NLPark-Cran/here.crina.at) 的
`backend/app/agentpool/`，本分支保存人格与配置模板，供其引用。

## 集成方式

- 后端按任务 spawn `kimi --wire -w <用户沙箱> --config-file <用户 kimi.toml>`，
  通过 stdio JSON-RPC（wire 协议 1.10）驱动：initialize → prompt →
  ContentPart/ToolCall/ToolResult/StatusUpdate/TurnEnd → result。
- 每用户独立沙箱目录（`/var/crina/users/<uid>/sandbox`），半隔离 = 进程级 + 目录级。
- provider 使用 `openai_legacy` 指向 TokenDance 网关（模型 qwen3.8-max），
  API Key 按用户注入（BYOK 词元蓄电池或站点配额 Key），不写入 worker 环境变量。
- 委托池上限 3 并发，单任务 15 分钟超时，事件落盘 jsonl 供回放。

## 文件

- `SANDBOX_AGENTS.md` — 写入每个用户沙箱的人格与约束（crina 干活形态）
- `kimi.toml.example` — 用户级 provider/模型配置模板
