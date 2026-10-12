# sync-hub

个人配置与数据同步中心 · 自动化更新，无需人工干预。

## 订阅输出

| 文件 | 格式 | 订阅地址 |
|---|---|---|
| `sub/v2ray.txt` | V2ray / base64 | https://raw.githubusercontent.com/wanerlin/sync-hub/main/sub/v2ray.txt |
| `sub/clash.yaml` | Clash | https://raw.githubusercontent.com/wanerlin/sync-hub/main/sub/clash.yaml |

## 更新机制

GitHub Actions 定时（每 6 小时）拉取上游源 → 解析 → 合并去重 → 自动提交。

上游订阅源存放在仓库 Secret `SUB_SOURCES`（JSON 数组），**不落盘、不公开、不进日志**。

## 手动触发

Actions → `update-subscriptions` → Run workflow
