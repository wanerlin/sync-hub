# sync-hub

个人配置与数据同步中心 · 自动化更新，无需人工干预。

---

## 📡 订阅地址（国内可用）

> ⚠️ **重要**：`raw.githubusercontent.com` 在国内已被墙（实测 HTTP 000 / 25s 超时）。
> 请使用下方**镜像地址**，功能完全等价、内容实时同步。

### Clash 订阅

| 优先级 | 镜像通道 | 订阅地址 | 实测 |
|:---:|---|---|---|
| 🥇 **首选** | GitHub Pages · Fastly CDN | `https://wanerlin.github.io/sync-hub/sub/clash.yaml` | 200 · 0.67s |
| 🥈 备用 | gh-proxy.com | `https://gh-proxy.com/https://raw.githubusercontent.com/wanerlin/sync-hub/main/sub/clash.yaml` | 200 · 0.54s |
| 🥉 备用 | ghfast.top | `https://ghfast.top/https://raw.githubusercontent.com/wanerlin/sync-hub/main/sub/clash.yaml` | 200 · 0.98s |
| 备用 | ghproxy.net | `https://ghproxy.net/https://raw.githubusercontent.com/wanerlin/sync-hub/main/sub/clash.yaml` | 200 · 1.46s |
| ⚠️ 慎用 | jsDelivr | `https://gcore.jsdelivr.net/gh/wanerlin/sync-hub@main/sub/clash.yaml` | **有缓存延迟** |

> 💡 jsDelivr 走 CDN 缓存，节点更新后可能仍返回旧版本，**不建议作为主力订阅**。

### V2ray 订阅

| 优先级 | 镜像通道 | 订阅地址 | 实测 |
|:---:|---|---|---|
| 🥇 **首选** | GitHub Pages | `https://wanerlin.github.io/sync-hub/sub/v2ray.txt` | 200 · 0.85s |
| 🥈 备用 | gh-proxy.com | `https://gh-proxy.com/https://raw.githubusercontent.com/wanerlin/sync-hub/main/sub/v2ray.txt` | 200 · 0.60s |

### 原始地址（需自备代理）

| 文件 | 地址 |
|---|---|
| `sub/clash.yaml` | `https://raw.githubusercontent.com/wanerlin/sync-hub/main/sub/clash.yaml` |
| `sub/v2ray.txt` | `https://raw.githubusercontent.com/wanerlin/sync-hub/main/sub/v2ray.txt` |

---

## 更新机制

- **本地推送**：AstrBot 侧 `update_sub.py` 定时拉源 → 去重 → sing-box 实测 → 生成成品 → 推送本仓库 `sub/`
- **云端兜底**：GitHub Actions `update-subscriptions`（每 6 小时）拉取上游源 → 解析 → 合并去重 → 自动提交
- **Pages 镜像**：每次 push 到 `main` 后，GitHub Pages 自动重建，约 1 分钟生效

上游订阅源存放在仓库 Secret `SUB_SOURCES`（JSON 数组），**不落盘、不公开、不进日志**。

---

## 手动触发

Actions → `update-subscriptions` → Run workflow

---

## 状态

- 最后更新：见 `sub/meta.json` 的 `updated` 字段
- 节点统计：见 `sub/meta.json` 的 `total_alive` 字段

---

*Maintained by 婉儿 (Waner) · 2026*
