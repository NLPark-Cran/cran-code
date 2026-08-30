# chaxunma（猹询码）

cran-code lite 分支的服务端受限 Agent 运行时：OpenAI 兼容协议 + 白名单工具 + 宿主注入的副作用回调。

## 设计

- **工具即权限边界**（借鉴 EVA）：模型只能 `list_files / read_file / patch_text / write_file / decide_config / deploy / ask_user / finish / fail`，没有 shell、没有网络、没有暂存区之外的文件访问。
- **loop 无 IO 依赖**：模型调用走注入的 base_url + key；`deploy` 是回调，由宿主（tt2-api）真正执行。因此 loop 可以在任何宿主里复用与测试。
- **TokenPay 计费友好**：异常携带 `TokenDance-Recovery-Action`，宿主可据此降级到共享免费池。

## 用法

```python
from pathlib import Path
from chaxunma import AgentLoop, ToolContext

loop = AgentLoop(
    api_key=user_tokendance_key,
    model="glm-5.3-flash",
    base_url="https://tokendance.space/gateway/v1",
    app_url="https://free.hub.tt2.li",  # X-App-URL 归因
)
ctx = ToolContext(staging=Path("/srv/tt2/staging/<task_id>"))
outcome = await loop.run(history, ctx, deploy=my_deploy_fn)
# outcome.kind: done / needs_input / failed / over_steps
```

## 测试

```bash
cd packages/chaxunma && uv run pytest
```
