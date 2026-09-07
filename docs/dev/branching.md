# 分支与发版规范（2026-09-07 确立）

## 分支

| 分支 | 用途 | 规则 |
|---|---|---|
| `main` | 唯一主干，始终可部署 | 直接提交仅限小修小补与文档；特性走短生命周期特性分支或直接在 main 原子提交（当前单人+agent 模式） |
| `crina` | 镜听空间集成分支 | 定期 `git merge main` 保持齐平；独有工件先落 main 再说 |
| 特性分支 | 大改动可选 | `feat/<name>`，合并后删除 |
| 上游镜像分支 | **不保留** | 上游分支一律不复制到 origin（2026-08-23 已清理 33 个）；需要时从 `upstream` remote 取 |

## 上游同步

- 基线冻结在 kimi-cli v1.49.0 / kosong 0.56.0（1.50 转入 kimi-code 迁移轨道，不再整体 merge）。
- 只 cherry-pick 安全/关键修复；每次 cherry-pick 记录到 `docs/dev/changelog.md`。
- `git fetch upstream` 后先看 `git log --oneline HEAD..upstream/main` 评估再动。

## 版本与发版

- 版本号跟随上游基线（`pyproject.toml`），平台自身演进不 bump 版本号，以部署 bundle hash + git commit 为追踪单位。
- 部署走 `cran-deploy` skill（`.kimi/skills/cran-deploy/SKILL.md`）；生产 bundle hash 记录在 AGENTS.md「当前状态」。
- 每个里程碑：changelog.md 归档 + AGENTS.md 状态行更新。

## Commit 纪律

- conventional 前缀（feat/fix/docs/chore/refactor/test），message 英文，正文随意。
- 作者身份：`NLPark-Cran <crina@tt2.li>`（repo-local config 必须有；见 conventions.md「Commit 身份纪律」）。
- 单 commit 保持原子可审；大型机械性改动（重命名/格式化）独立成 commit。
