# web/ — 多用户平台层

> 安全红线密集区。任何新端点先想鉴权和越权。

## 地图

| 文件 | 职责 |
|---|---|
| `app.py` | FastAPI 装配 + SPA 兜底（规范化后 /api 绝不兜底成 index.html） |
| `auth.py` | v1 session-token 中间件 + Origin 检查 + LAN-only |
| `auth_v2/jwt.py` | v2 JWT；`require_user`/`require_admin` |
| `api/sessions.py` | v1 会话 API + WS stream + 分页重放 + goal/subagents 端点（1.9k 行，考虑拆分） |
| `api_v2/` | 平台 API（teams/users/projects/providers/keyproxy/admin/fs/git/terminal/collab/memories） |
| `runner/process.py` | SessionProcess：worker 生命周期/锁/广播/key 注入/闸门（`_lock` 临界区勿持锁 restart） |
| `runner/worker.py` | worker 子进程入口 |
| `store/sessions.py` | 会话索引（磁盘扫描+缓存） |
| `db/` | sqlite 11+ 表；`connection.py::_ensure_column` 幂等迁移；`tz.py` 时区桶 |

## 本目录专属纪律

- v1 端点鉴权三件套：`get_session_or_404` → `can_access_session(state, user, await get_user_team_ids(user))` → 业务。
- v2 端点默认 `require_user`，管理动作 `require_admin`。
- 文件服务：`resolve()` + `is_relative_to()`，防遍历/符号链接逃逸。
- 主进程与 worker 的共享状态：会话目录 JSON 文件即 IPC（goal.json 模式），worker 在 turn 边界重读。
- 密钥永不进日志/响应体；`config.toml` 输出需脱敏。
