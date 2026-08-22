---
name: cran-deploy
description: Deploy Cran Code (backend uv tool + frontend statics) to crys.tt2.li safely. Use when the user asks to deploy, restart the service, or ship changes to production.
---

# cran-deploy

生产部署 SOP。完整版见 `docs/dev/deploy.md`；此处为执行清单。

## 步骤

1. **预检**：`uv run pytest tests/web/ -q` 全绿；前端改动时 `npx tsc -b --noEmit` + `npx vitest run` 通过。
2. **后端**：
   ```bash
   uv tool install --force --refresh --from . cran-code   # --refresh 不可省
   ```
3. **前端**（仅 web/src 有改动时）：
   ```bash
   cd web && NODE_OPTIONS="--max-old-space-size=1800" npm run build
   cp -r dist/* ../src/cran_code/web/static/
   cp -r dist/* /root/.local/share/uv/tools/cran-code/lib/python3.14/site-packages/cran_code/web/static/
   ```
4. **重启 + 验证**：
   ```bash
   systemctl restart cran-code.service && sleep 10
   curl -s https://crys.tt2.li/ | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1   # bundle hash 应与新构建一致
   journalctl -u cran-code.service -n 50 --no-pager | grep -i "error\|traceback" # 应为空
   ```
   刚重启 10-30 秒内 502 属正常，稍等重试。
5. **冒烟**：`/api/v2/providers/` 未授权应 401；如改了 worker 链路，开一个测试会话发一条消息。

## 红线

- 不提交 `~/.cran/config.toml` / `server.env` / 任何密钥。
- 静态目录要同步**两处**（仓库 + 已安装工具目录）。
- 用户正在跑会话时先告知再重启（重启会杀所有 worker；会话可恢复但进行中的轮次会断）。
