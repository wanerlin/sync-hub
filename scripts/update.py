#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订阅聚合更新器
读取环境变量 SUB_SOURCES（JSON 数组，元素为订阅链接）
拉取 -> 解析 -> 合并去重 -> 输出 sub/v2ray.txt 与 sub/clash.yaml
"""
import os, sys, json, base64, re, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sub"
OUT.mkdir(exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (compatible; sync-hub/1.0)"}

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def b64d(s):
    s = re.sub(r"\s+", "", s)
    return base64.b64decode(s + "=" * (-len(s) % 4))

def parse_any(raw: bytes):
    """返回 (links:list[str], clash_proxies:list[dict])"""
    text = raw.decode("utf-8", "ignore").strip()
    links, proxies = [], []

    # 1) 纯 base64 的 v2ray 订阅
    try:
        dec = b64d(text).decode("utf-8", "ignore")
        if "://" in dec:
            text = dec
    except Exception:
        pass

    # 2) Clash YAML
    if re.search(r"^\s*proxies\s*:", text, re.M):
        try:
            import yaml
            data = yaml.safe_load(text) or {}
            for p in (data.get("proxies") or []):
                if isinstance(p, dict) and p.get("type"):
                    proxies.append(p)
            return links, proxies
        except Exception as e:
            print(f"  [warn] clash 解析失败: {e}")

    # 3) 明文链接（ss:// vmess:// trojan:// vless:// hysteria2:// tuic://）
    for line in text.splitlines():
        line = line.strip()
        if re.match(r"^(ss|ssr|vmess|vless|trojan|hysteria2?|hy2|tuic)://", line):
            links.append(line)
    return links, proxies

def dedup(seq, key=None):
    seen, out = set(), []
    for x in seq:
        k = key(x) if key else x
        if k not in seen:
            seen.add(k); out.append(x)
    return out

def main():
    raw_src = os.environ.get("SUB_SOURCES", "").strip()
    if not raw_src:
        print("SUB_SOURCES 为空，退出"); return 1
    try:
        sources = json.loads(raw_src)
        if isinstance(sources, str): sources = [sources]
    except Exception:
        sources = [s.strip() for s in raw_src.splitlines() if s.strip()]

    all_links, all_proxies = [], []
    for i, url in enumerate(sources, 1):
        try:
            body = fetch(url)
            l, p = parse_any(body)
            print(f"  [{i}/{len(sources)}] {url[:48]}... -> links={len(l)} proxies={len(p)}")
            all_links += l; all_proxies += p
        except Exception as e:
            print(f"  [{i}/{len(sources)}] 拉取失败: {e}")

    all_links = dedup(all_links)
    all_proxies = dedup(all_proxies, key=lambda p: (p.get("server"), p.get("port"), p.get("type")))

    # 输出 v2ray base64
    if all_links:
        (OUT / "v2ray.txt").write_text(
            base64.b64encode("\n".join(all_links).encode()).decode(), encoding="utf-8")
    # 输出 clash
    if all_proxies:
        names = [p.get("name", f"node-{i}") for i, p in enumerate(all_proxies)]
        cfg = {"port": 7890, "socks-port": 7891, "allow-lan": False, "mode": "rule",
               "log-level": "info",
               "proxies": all_proxies,
               "proxy-groups": [{"name": "PROXY", "type": "select", "proxies": names + ["DIRECT"]}],
               "rules": ["MATCH,PROXY"]}
        import yaml
        (OUT / "clash.yaml").write_text(
            yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print(f"完成：链接 {len(all_links)} 条，Clash 节点 {len(all_proxies)} 个")
    return 0

if __name__ == "__main__":
    sys.exit(main())
