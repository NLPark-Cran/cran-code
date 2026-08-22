# 部署 SOP（crys.tt2.li 生产环境）

> 服务：`cran-code.service`（systemd），uv tool 安装于 `/root/.local/share/uv/tools/cran-code/`，端口 5496，Nginx 反代 crys.tt2.li，`--public` 模式。启动脚本 `/usr/local/bin/cran-code-web` 会 source `~/.cran/server.env`。

## 后端

```bash
cd /root/workspace/crys
uv tool install --force --refresh --from . cran-code   # --refresh 必须！否则可能复用旧 wheel 缓存
systemctl restart cran-code.service
sleep 10
curl -s -o /dev/null -w "%{http_code}\n" https://crys.tt2.li/   # 期望 200（刚重启可能短暂 502，等几秒再试）
```

验证安装内容（防缓存坑）：

```bash
grep -c "<新函数/特征串>" /root/.local/share/uv/tools/cran-code/lib/python3.14/site-packages/cran_code/<file>.py
```

## 前端

```bash
cd /root/workspace/crys/web
NODE_OPTIONS="--max-old-space-size=1800" npm run build   # 约 2-10 分钟
cp -r dist/* ../src/cran_code/web/static/                # 仓库内静态目录
cp -r dist/* /root/.local/share/uv/tools/cran-code/lib/python3.14/site-packages/cran_code/web/static/  # 已安装工具目录
systemctl restart cran-code.service
# 验证：served index.html 的 bundle hash 与新构建一致
curl -s https://crys.tt2.li/ | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1
```

## 数据库

- 新表：`db/models.py` 添加模型即可（启动时 `create_all` 自动建表）。
- 已有表加列：无自动迁移，需手工 SQL 或写迁移脚本。

## 配置变更

- `~/.cran/config.toml` 改动后：worker 在下次启动时读取；可用 `POST /api/v2/providers/select`（admin）触发运行中 worker 重启，或直接重启服务。
- **永远不要**把 config.toml / server.env 提交进仓库。

## 回滚

- 代码：`git revert` 或 checkout 旧 commit 后重新走后端部署流程。
- 前端：重新构建旧版本 dist 并同步两个静态目录。
- 数据库：本项目无降级迁移；改表前备份 `~/.cran/cran.db`。

## 部署后验证清单

1. `https://crys.tt2.li/` 200；bundle hash 正确。
2. `/api/v2/providers/` 未授权 401。
3. `journalctl -u cran-code.service -n 50 --no-pager` 无新 traceback。
4. 真实开一个会话发消息，确认 worker 正常（`/px` 或直连按 key 来源走通）。
