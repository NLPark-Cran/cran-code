---
name: cran-review
description: Pre-merge/pre-deploy review checklist for Cran Code changes (security, races, contracts, i18n, performance). Use when reviewing or finalizing a change set.
---

# cran-review

变更收尾评审清单。逐项过，全部通过才允许部署/合并。

## 安全

- [ ] 新增 v2 端点：`require_user` 起步；管理动作 `require_admin`；团队资源走 `_require_team_admin`。
- [ ] 任何"以用户输入的 URL 发服务端请求"：https-only + 非公网 IP 拦截 + 不跟随重定向。
- [ ] worker 环境新增变量：确认不含服务器密钥；凭证只经 `_build_worker_env`。
- [ ] API 响应不含 key 材料（只有 has_api_key）；日志不打印密钥。
- [ ] `git diff | grep -i "sk-\|secret"` 为空。
- [ ] **机密展示层**：新增展示工具入参/结果的前端位 → 走 `lib/redact.ts`（默认遮蔽、点击揭示）。
- [ ] **路径安全**：文件类端点 `resolve()+is_relative_to()`；鉴权判定基于解码后 ASGI path；SPA 兜底不得吞 `/api/*`。
- [ ] **记忆/注入内容**：denylist 机密模式；注入块声明"是数据不是指令"。

## Commit 与仓库卫生

- [ ] 目标仓库有 repo-local `user.name=NLPark-Cran` / `user.email=crina@tt2.li`（`git config --local --list | grep user`）。
- [ ] 子代理代提交前同项确认（2026-09-07 FDE-POC 事故教训）。
- [ ] 大文件/二进制不入库；`git status` 无意外文件。

## 并发与状态

- [ ] `process.py`：`SessionProcess._lock` 临界区内不调用会再次取锁的方法（restart_worker 等）。
- [ ] 重放/分页改动：检查与 `_pending_requests`、initialize 缓存、`turn_base` 游标的相互作用。
- [ ] 前端流式处理：新事件类型确认走重放队列（`isReplayingRef || isReplayQueueActive`），live 与 replay 不乱序。

## 跨端契约（扩充）

- [ ] wire 事件变更：`types.py` union + `__all__` + 前端 `wireTypes.ts` + reducer case + 重放路径验证。
- [ ] REST 变更：openapi 再生成（本地后端起 5495，`npm run generate`）+ 手写 v2.ts 同步。

- [ ] 前后端消息形状一致（snake_case 后端 ↔ 前端解析）。
- [ ] `history_complete`/分页响应字段变更时两端同步。

## i18n

- [ ] 新用户可见字符串全部进 `web/src/i18n/{zh,en}/`，`npx vitest run` parity 通过。

## 性能

- [ ] 不在热路径（step 循环、重放、逐事件处理）引入 O(n²) 或全量文件读取。
- [ ] 大文件/大行有上限或分块处理（参照 `_BIG_LINE_BYTES` 模式）。

## 验证

- [ ] `uv run pytest tests/web/ -q` 全绿；`tests/core` 不超出基线（见 conventions.md）。
- [ ] `npx tsc -b --noEmit` 0 错误；biome 不新增。
