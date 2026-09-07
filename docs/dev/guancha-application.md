# 观猹 OAuth2.0 接入申请材料（待提交）

> 申请表单：https://agentuniverse.feishu.cn/share/base/form/shrcnHJ3ATlNg6ofNHssT2zK7Dh
> 填表后需联系观猹官方人员对接；拿到 client_id/client_secret 后接入（文档：`docs/references/` 或 here.crina.at 的《观猹认证接入文档》）。

## 客户端注册信息（建议填写）

| 参数 | 值 | 说明 |
|---|---|---|
| name | 猹询码 Cran Code | 授权页展示：「猹询码 Cran Code 请求获取权限」 |
| domain | https://crys.tt2.li | 回调 URI schema；回调地址为 `https://crys.tt2.li/api/v2/auth/guancha/callback`（待开发） |
| allowed_scopes | `read email` | 基础信息 + 邮箱（登录绑定用；手机号暂不需要） |
| is_public | false | 机密客户端（有后端安全存储 secret，存 `~/.cran/server.env`） |

## 洛书侧（后续第二个客户端）

洛书（Tauri 本地客户端）届时需注册为 **公开客户端**（is_public=true + PKCE），回调走 loopback：`http://127.0.0.1:<port>/oauth/callback`。

## TokenPay/TokenDance 归因

已就位：`X-App-Name: Cran Code` + `X-Site-URL: https://crys.tt2.li` 随所有 TokenDance 流量上报（2026-08-18 上线）。成为合作项目方后按归因统计分润。
