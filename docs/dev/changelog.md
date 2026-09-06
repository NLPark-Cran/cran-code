# 开发里程碑（归档自 AGENTS.md 的历史记录）

## 2026-06-08 — upstream v1.49.0 合并 + K3 支持
- 合并 MoonshotAI/kimi-cli v1.49.0（kosong 0.55.0）；新增 K3 / kimi-for-coding-highspeed 支持。

## 2026-07-19/20 — Providers 功能 + initialize 重放 + 安全大修 + key 体系
- Providers v2 API + ProvidersPage（模型选择/切换重启 worker）。
- AskUserQuestion/K3 修复：initialize 缓存重放（worker 重启不丢客户端能力）。
- 20 项安全审查修复（SSRF、角色、限流、fs 防护、toml 脱敏等）；require_admin + 零 admin 引导。
- Key 体系：个人/团队/共享三级解析、/px 代理、配额与用量计量、prompt 闸门。
- 二轮审查：代理令牌加固（JWT 密钥签名、3 天 TTL、loopback-only、路径白名单）、kimi 系也走代理、v1 config PATCH 收 admin。

## 2026-07-21 — 前端全面进化
- i18n 全套（react-i18next，11 命名空间，zh 默认 + English 切换）。
- UX：工具调用卡片（运行展开/完成折叠/分组）、ContextRing + StatusPanel、压缩分隔线、已压缩媒体占位片。
- 性能：shiki 裁 31 语言、refractor 300→22、manualChunks → dist 20MB→12MB、chunk 358→52。
- 用量统计页 /settings/usage；会话分叉/标题/归档打磨。
- 修复：压缩后图片重放（tombstone）、ReadMediaFile 压缩（2000px 保格式）。

## 2026-07-26/27 — 重放冻结与重连循环修复 + 控制台化
- 流式碎片合并（131K→2.3K 帧）+ 分片重放；分页重放（最新一页 + 游标加载更早）。
- session_status 竞态导致的无限重连修复；控制台式 /dashboard；Layout 滚动壳修复；文本残段吸收。
- DB NullPool + WAL（QueuePool 耗尽修复）。

## 2026-07-27/08-09 — 兼容性修复
- TD 网关 413/瞬时 400 → 溢出压缩重试；代理令牌过期自动刷新；pending 问题补发；initialize 缓存应答。
- 三轮审查：fork turnIndex 绝对化、分页边界 turn 对齐、initialize 空窗排队、重放队列排序等。

## 2026-08-18 — 上游 merge + 社区 PR + kimi-code 借鉴
- merge upstream/main（kosong 0.56.0；behind 归零）。
- 移植社区 PR：#2507 #2520 #2572 #2530 #2592 #2539 #2535。
- compaction prompt 第一人称化 + 摘要不可信前缀 + token 计数含 overhead。
- system.md 升级（去过度主动、预告纪律、拒绝不绕路、爆炸半径、注入硬化、CANDID、语言跟随）。
- TokenDance 应用标识（X-App-Name/X-Site-URL）。

## 2026-08-18 — 媒体 blob-ref 外置
- `soul/blobstore.py`：context.jsonl 落盘时把 ≥1KB 的 data: URL 媒体外置为 `blobs/<sha256>.<ext>`（内容寻址去重），restore 时水合回 data URL；blob 缺失/引用非法降级为文本占位片，restore 不炸。
- 内存模型 / wire / 各 provider 序列化零改动；wire.jsonl 刻意不外置（前端重放需内联渲染）。
- fork 按 context 行中的 blobref 引用复制 blob；revert/clear 轮转保留 blobref，blob 随会话目录同生同灭。
- 测试：tests/core/test_blobstore.py 17 例（单元 + Context 集成 + revert + fork）。

## 2026-08-18 — swarm 可视化
- wire 新事件 SubagentStatus（实例创建/状态变更时由 SubagentStore 单一 choke point 发射，前台后台均覆盖；shell/ACP 默认忽略）。
- GET /api/sessions/{id}/subagents 快照端点（meta.json 直读，鉴权同 fork）。
- 前端：zustand swarm store + 会话切换时快照水合（竞态安全）+ chat header SwarmPanel（运行数徽章/状态点/步数/相对时间）；Notification 事件接 toast（重放时不刷）。

## 2026-07-27 — Goal 模式 P1（后端核心）
- `soul/goal.py`：`GoalStore`（原子写 `<session_dir>/goal.json`）+ 状态机（active/paused/blocked，complete 瞬态清除）、turns/tokens/active_seconds 统计、预算检查（≥75% 压力提示）、`GoalDriver`（传输层无关、可单测）。无显式 turns 预算时默认 30 轮封顶（`DEFAULT_GOAL_TURN_BUDGET`，cran-code 偏离上游以保护配额）。
- 工具 `tools/goal/`：CreateGoal（审批门控）/GetGoal/UpdateGoal/SetGoalBudget，root-only；UpdateGoal+SetGoalBudget 无 goal 时隐藏（wire initialize + 工具迁移时双向同步）。
- Driver 接入 `WireServer._handle_prompt`：turn 边界注入 reminder（active 全量 / paused·blocked 轻量），turn 后记账续跑；错误/取消 → pause 后返回原 JSONRPC 映射；MaxStepsReached 计入完成 turn。
- wire 事件 `GoalUpdated`（snapshot + change；预算耗尽阻塞用 change="budget"）；会话加载时 active→paused 降级（`KimiCLI.create`，stop_reason="session restarted"）；fork 不继承 goal.json。
- 测试：tests/core/test_goal.py 37 例 + fork 用例；tests/core 失败数与已知基线一致（30F+5E）。

## 2026-08-18 — Goal 模式（P1 核心 + P2 Web UX）
- P1：`soul/goal.py`（GoalRecord/GoalStore/GoalDriver/预算/注入 prompt）+ 4 个 root-only 工具 + GoalUpdated wire 事件 + WireServer driver 循环（续跑/MaxSteps 续驱/错误停车/恢复降级）+ 默认 30 轮安全上限。
- P2：REST GET/POST/DELETE /goal + pause/resume；worker 每个 prompt 重同步工具可见性（goal.json 即 IPC）；前端 goal store + GoalBanner（状态/统计/暂停/恢复/取消）+ 完成 toast。
- 设计文档：docs/dev/goal-mode.md（移植自 kimi-code GOAL.md）。

## 2026-08-18 — 千问办公风视觉收敛
- 设计 token：品牌紫主色（light #615CED / dark 浅紫）、冷灰画布 #f6f7fb、圆角 0.75rem、更软边框、分层柔和阴影、紫色 ring/sidebar 强调。
- 登录页：CSS 紫蓝径向背景 + rounded-2xl 悬浮卡片 + 渐变品牌标题；全站经 token 自动继承。

## 2026-08-23 — 工程化 + 安全加固 + 多主题系统 + read-before-write
- 安全审计（对标 kimi-code 0.25.0）：无 %-encoding 鉴权绕过（中间件/路由同用 ASGI 解码 path）；符号链接逃逸已被 resolve()+is_relative_to 拦截；修复 SPA 兜底吞掉非规范化 /api 路径的问题；新增 tests/web/test_security_regressions.py（6 例）。
- 分支精简：origin 删除 33 个上游镜像分支；crina 分支保留（独有文档已拣入 main）。
- 工程化：README 全量重写（反映平台现状）；AGENTS.md 刷新为抗 compact 记忆锚点；conventions.md 扩充为完整工程规范（结构规范/模式库/测试配方/配置清单/行为纪律）；pyright strict 配置修正为 src/cran_code。
- 多主题系统：石墨靛蓝灰（默认）/朱砂粉金/青碧 × 浅色+深色 六组合；头部快捷切换 + 设置页外观 tab；localStorage 持久化（cran-color-theme）；毛玻璃 header/侧栏；登录页背景随主题。
- read-before-write 纪律（移植 kimi-code 0.38.0）：WriteFile/StrReplaceFile 拒改未读文件；工具描述快照刷新为绿。
- WaitFor 评估结论：TaskOutput(block=true, timeout) 已等价，不重复造轮子；长输出折叠前端 SmartTool 已有。

## 2026-08-23 — 时区化用量统计 + 图表修复 + 控制台集成
- 用量日桶支持 IANA 时区（`/users/me/usage/daily` 与 `/admin/usage` 加 `tz` 参数；修复"今日"实为"UTC 最近 24h"的问题）；`teams.timezone` 列（ensure_column 幂等迁移）+ TeamPage 时区选择器（owner/admin）。
- 图表根因修复：SVG `preserveAspectRatio="none"` 拉伸文字 → 标签改 HTML 覆盖层；x 轴稀疏到 ≤8 个 MM-DD；数值标签拥挤时隐藏；分段色改语义 token（暗色可见）。
- 控制台统计卡片压扁；用量页团队区显示生效时区并链接团队页。
- generate-api.sh 修复：保留手写 v2.ts、跳过 /px catch-all 的重复 operationId 校验；注意 5494 是保留的上游 kimi-cli 端口，本地 cran 后端用 5495 生成客户端。

## 2026-09-07 — 证书事故修复 + 底座快赢（环境模板/git 必备/脱敏/bug 包）
- 运维：crys.tt2.li 证书续期（根因 standalone 续期器与 nginx 抢 80 端口；已改 nginx authenticator）。
- 每用户环境模板：`users.env_template` + PATCH /users/me + 会话首 prompt 注入 `<user-environment>`（wire 空时一次性注入，匿名/文件上传流不受影响）+ 设置页"环境"tab。
- 会话创建自动 `git init`（显式 work_dir；跳过 home 与已有仓库）。
- 机密脱敏：`lib/redact.ts` + RedactedText/RedactedCodeBlock，工具卡片默认遮蔽 PAT/sk-/cwk_/Bearer/key=value 类机密，点击揭示。
- Teams 页并行加载改 allSettled（局部失败不再整页报错）；GitPanel 对非 git 目录显示友好空态。
- 决策：上游冻结 1.49 基线（1.50 已转入 kimi-code 迁移轨道，1118 提交分叉，不再 merge；后续只 cherry-pick 安全修复）。
- 洛书项目启动：github.com/NLPark-Cran/luoshu（定位/素材/ADR 001 壳选型 Tauri + ADR 002 记忆架构）。
