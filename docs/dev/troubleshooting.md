# 故障索引（症状 → 根因 → 修复）

> 遇到似曾相识的症状先查这里。每条含定位方法。

## 会话/连接类

### 刷新后会话卡死、WS 反复报错、对话"消失"（2026-07-26 修复）
- **症状**：长会话刷新后页面冻结，"Websocket 连接错误"。
- **根因**：wire 日志 98% 是流式碎片（13 万条），全量重放 + 前端 O(n²) 合并把标签页卡死。
- **修复**：重放时服务端合并连续碎片（13 万→2.3 千帧）+ 前端 200 条/宏任务分片处理。`sessions.py::_try_merge_delta`、`useSessionStream.ts` 重放队列。
- **定位**：`wc -l <session>/wire.annotated.jsonl`；看 ContentPart/ToolCallPart 占比。

### 会话无限重连（"一直刷新"）（2026-07-27 修复）
- **根因**：分片重放引入的竞态——`session_status` 快照在 15 秒看门狗定时器设置之前就被处理，导致定时器永远触发重连。
- **修复**：`sessionStatusSeenRef`（已到就不再设看门狗）。
- **定位**：浏览器 Console 找 `[SessionStream] session_status timeout ... reconnecting`。

### 会话卡"正在连接"，AskUserQuestion 无法作答（2026-08-08 修复）
- **根因**：`wire.annotated.jsonl` 不记录 JSONRPC 请求类消息 → 重连后待答问题丢失，会话显示 busy 但无对话框。
- **修复**：`SessionProcess._pending_requests` 跟踪未答请求，新连接补发（`send_pending_requests`）。
- **定位**：看 wire.jsonl 尾部是否有 QuestionRequest；探针连 WS 看是否收到 `method: "request"`。

### 斜杠命令（/compact 等）消失（2026-08-09 修复）
- **根因**：initialize 去重（L9/L20）把重复 initialize 整个丢弃，客户端拿不到含 slash_commands 的响应。
- **修复**：缓存 worker 的 initialize 结果，去重的 initialize 用缓存应答；worker 初始化期间的等待者排队（`_deduped_initialize_ids`）。

## Provider/LLM 类

### TokenDance 报 413 / "Error when parsing request"（2026-08 修复）
- **根因**：TD 网关的请求体字节上限（多图 base64 膨胀）+ 网关对瞬时上游故障报笼统 400。
- **修复**：溢出分类器（413/token-limit 400/该特定 400 消息）→ 压缩后重试该步（`kimisoul.py::_is_provider_overflow_error`）；重试次数默认 10。
- **定位**：`~/.cran/logs/kimi.log` 找 `APIStatusError`；可用"忠实重放"脚本直接打上游验证（见会话 notes）。

### /px/v1 401 "Invalid or missing key proxy credential"（2026-08-07 修复）
- **根因**：cwk_ 令牌 3 天 TTL，长寿 worker 持有过期令牌。
- **修复**：`_needs_proxy_token_refresh`，新 prompt 前自动重启空闲 worker 换令牌（force=False 不杀忙 worker）。

### 所有 DB 端点超时（QueuePool limit reached）（2026-07-27 修复）
- **根因**：sqlite 默认池 5+10 在代理+计量+闸门并发下耗尽。
- **修复**：sqlite 用 NullPool + WAL + busy_timeout；代理 3 次 DB 会话合并为 1 次。**勿恢复连接池**。

## 前端类

### /dashboard 无法滚动（2026-07-27 修复）
- **根因**：`index.css` 为聊天壳把 body/#root 设成固定高 + overflow hidden，v2 页面无自己的滚动容器。
- **修复**：Layout 改 `h-full flex-col` + main `flex-1 overflow-y-auto`。

### 消息出现 1-2 字残段（如单独的"本"）（2026-07-27 修复）
- **根因**：前端在 step 边界把跨界文本流切成两条消息，服务端文本其实完整。
- **修复**：`resetStepState(true)` 吸收 ≤2 字符残段。
- **定位**：对照 `wire.annotated.jsonl`，文本流是否连续。

### 压缩前的图片重启后重现（2026-07-21 修复）
- **根因**：annotated 文件不记录压缩事件 → 重放永不截断。
- **修复**：压缩事件写入 annotated + 重放 tombstone 旧媒体。

## 环境/部署类

- **服务重启后 502 几十秒**：正常（启动慢），等 10-20s 再 curl。
- **uv 重装后代码没变**：忘了 `--refresh`。
- **前端改动没生效**：静态文件要同步两个目录（仓库 + 已安装工具目录），并确认 bundle hash。

## 安全：路径规范化与鉴权一致性（2026-08-23 审计，对标 kimi-code 0.25.0 两例 CVE 级修复）

**结论**：中间件与路由都用 ASGI `scope["path"]`（uvicorn 已解码 percent-encoding），解释一致 → 无 `%2F` 鉴权绕过。符号链接逃逸由 `resolve()` + `is_relative_to()` 在所有 fs/会话文件端点强制拦截。

**实际修复**：SPA 兜底原先把 `//api/*`、`/../api/*` 这类非规范化路径回退成 index.html（200），现在统一规范化后判定，命中 `/api/` 前缀的一律 404（`web/app.py::SPAStaticFiles`）。

**回归测试**：`tests/web/test_security_regressions.py`（raw_path 级，httpx 会规范化 `//` 和 `%2e`，测试必须用 `raw_path` 构造）。

**已知信任模型假设**（非 bug，勿"修复"）：worker 以服务用户身份执行 shell（root），多用户隔离依赖配额/审批/团队边界而非 OS 沙箱；`create_session` 接受任意 work_dir 是平台设计（用户自带项目目录）。如未来开放不可信用户，需先做 OS 级隔离。

## 运维：证书过期续期失败（2026-09-07）

**症状**：crys.tt2.li 证书过期（浏览器告警/无法访问）。
**根因**：该域名的 certbot renewal 配置用了 `standalone` authenticator，续期时要独占 80 端口，与常驻 nginx 冲突 → 自动续期静默失败。
**修复**：`certbot renew --cert-name crys.tt2.li --force-renewal --nginx`（手动续上）+ 把 `/etc/letsencrypt/renewal/crys.tt2.li.conf` 的 `authenticator = standalone` 改为 `nginx`（与其它域名一致），`systemctl reload nginx`。
**预防**：新域名签证书一律用 `--nginx`；可用 `grep -l "standalone" /etc/letsencrypt/renewal/*.conf` 排查遗留。
