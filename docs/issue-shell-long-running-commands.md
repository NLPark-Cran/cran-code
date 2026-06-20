# Issue 素材：Shell 工具执行长耗时命令稳定性问题

> 汇总人：Cran Code 会话代理  
> 时间：2026-06-20  
> 关联项目：`/root/workspace/test0607/test6`（FindX）

---

## 建议标题

`[Bug] Shell 工具执行长耗时命令时频繁触发 Session Error / Tool execution cancelled / "Unexpected token '<'"`

---

## 环境信息

| 项目 | 内容 |
|---|---|
| 工作目录 | `/root/workspace/test0607/test6` |
| 前端 | Next.js `16.2.9` + React `19.2.4` + next-intl `4.13.0` + Tailwind v4 |
| 后端 | FastAPI + Python 3.13，PM2 进程 `findx-backend` |
| 域名 | `findx.hub.tt2.li` |
| 会话类型 | Kimi Code CLI / Cran Code 交互式会话 |

---

## 已确认正常的部分（排除项目代码问题）

1. **后端健康**  
   `curl http://127.0.0.1:8006/health` 返回 `{"status":"ok"}`。

2. **前端类型检查通过**  
   在 `/root/workspace/test0607/test6/frontend` 执行：
   ```bash
   npx tsc --noEmit
   ```
   退出码 `0`，无任何类型错误。

3. **已修复的前端问题**  
   - `i18n/routing.ts` 中 `createNavigation` 误从 `next-intl/routing` 导入，已改为从 `next-intl/navigation` 导入。
   - 页面已按 next-intl v4 规范迁移到 `app/[locale]/...`。
   - 已创建 `lib/api.ts`、`lib/store.ts` 并在 `battle/arena/agent/dashboard` 页面接入。

---

## 复现步骤

在 Cran Code 会话中执行任意**耗时超过约 10–20 秒**的 Shell 命令，例如：

```bash
cd /root/workspace/test0607/test6/frontend
npm run build > /tmp/findx-build.log 2>&1
```

或

```bash
cd /root/workspace/test0607/test6/frontend
npx next build
```

---

## 实际表现

命令不会正常结束，而是被 Cran Code 平台中断，出现以下错误之一：

### 1. Session Error（最常见）

```
Session Error: Unexpected token '<', "<html> <h"... is not valid JSON
```

### 2. Tool execution cancelled

```
Tool execution cancelled
```

### 3. No stderr

```
No stderr
```

### 4. 日志被截断

即使将 `stdout`/`stderr` 重定向到文件（`/tmp/findx-build.log`），日志也只能写到构建开始阶段：

```
> frontend@0.1.0 build
> next build

⚠ Warning: Next.js inferred your workspace root, but it may not be correct.
...
▲ Next.js 16.2.9 (Turbopack)

⚠ The "middleware" file convention is deprecated. Please use "proxy" instead.
  Creating an optimized production build ...
```

之后进程/输出被切断，没有后续构建阶段（编译、静态生成、打包）的日志。

---

## 期望表现

Shell 工具应能完整执行耗时命令（如 `npm run build`，通常 30–120 秒），并在完成后返回退出码和完整输出；若超时，应给出明确的超时提示和已生成的日志路径，而不是 JSON 解析失败的 Session Error。

---

## 影响

该问题导致**无法通过 Cran Code 完成前端生产构建和部署**。当前前端代码已就绪，但无法生成 `frontend/.next/standalone`，也就无法启动 `next start -p 3006` 并通过 Nginx 对外提供服务。

---

## 已尝试的规避手段（均无效或部分有效）

| 手段 | 结果 |
|---|---|
| 输出重定向到日志文件 | 日志仍被截断，命令被中断 |
| 缩短/拆分命令 | `npx tsc --noEmit` 等短命令可完成；任何完整构建命令都失败 |
| 清理 `node_modules` 重装 | 安装过程本身也会因同样原因中断 |
| 修复已知 TS/路由错误 | 已修复，但无法验证构建产物 |

---

## 建议排查方向

1. **心跳/超时机制**：检查 Shell 工具长命令执行时的心跳保活逻辑，是否在等待响应期间误把 HTML 错误页当 JSON 解析。
2. **输出缓冲区**：确认大体积 `stdout`/`stderr` 是否被正确流式回传，还是被截断后触发异常。
3. **后台任务边界**：明确区分“用户进程后台运行”与“工具本身执行超时”的报错信息，避免 `Session Error` 掩盖真实原因。
4. **Next.js/Turbopack 兼容性**：虽然更可能是工具层问题，但仍可验证 Next.js 16 + Turbopack 在目标容器中的构建是否被 OOM 或信号终止。

---

## 临时绕过方案

在 Cran Code 修复前，可在服务器终端直接执行：

```bash
cd /root/workspace/test0607/test6/frontend
npm run build
```

构建成功后，用 PM2 启动前端：

```bash
cd /root/workspace/test0607/test6
pm2 start ecosystem.config.js
```
