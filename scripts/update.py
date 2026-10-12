#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync-hub 订阅聚合更新器 (v2)

流程: 拉取 -> 解析(Clash/base64/明文) -> 链接转Clash -> 合并去重 -> 输出
输出: sub/clash.yaml , sub/v2ray.txt

订阅源优先级:
  1) 环境变量 SUB_SOURCES (JSON 数组 或 换行分隔)  —— 配置了就用它
  2) 否则使用内置 DEFAULT_SOURCES (公开免费源)
"""
import os, sys, json, base64, re, urllib.request, urllib.parse
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sub"
OUT.mkdir(exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (compatible; sync-hub/1.0)"}

DEFAULT_SOURCES = [
    "https://raw.githubusercontent.com/freefq/free/master/v2",
    "https://raw.githubusercontent.com/Pawdroid/Free-servers/main/sub",
    "https://raw.githubusercontent.com/ermaozi/get_subscribe/main/subscribe/v2ray.txt",
    "https://raw.githubusercontent.com/ripaojiedian/freenode/main/clash",
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.txt",
    "https://raw.githubusercontent.com/mahdibland/ShadowsocksAggregator/master/Eternity.txt",
]

LINK_RE = re.compile(r"^(ss|ssr|vmess|vless|trojan|hysteria2?|hy2|tuic)://", re.I)


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def b64d(s):
    s = re.sub(r"\s+", "", s).replace("-", "+").replace("_", "/")
    return base64.b64decode(s + "=" * (-len(s) % 4))


# ---------------- 明文链接 -> Clash 节点 ----------------

def _qget(q, k):
    v = q.get(k)
    return v[0] if v else None


def vmess_to_clash(link):
    try:
        j = json.loads(b64d(link[8:]).decode("utf-8", "ignore"))
        host, uid = j.get("add"), j.get("id")
        port = int(j.get("port", 0) or 0)
        if not host or not uid or not port:
            return None
        p = {"name": j.get("ps") or "vmess-%s" % host, "type": "vmess",
             "server": host, "port": port, "uuid": uid,
             "alterId": int(j.get("aid", 0) or 0),
             "cipher": j.get("scy") or "auto", "udp": True}
        if str(j.get("tls", "")).lower() in ("tls", "true", "1"):
            p["tls"] = True
            sni = j.get("sni") or j.get("host")
            if sni:
                p["servername"] = sni
        net = (j.get("net") or "tcp").lower()
        if net == "ws":
            p["network"] = "ws"
            p["ws-opts"] = {"path": j.get("path") or "/"}
            if j.get("host"):
                p["ws-opts"]["headers"] = {"Host": j["host"]}
        elif net == "grpc":
            p["network"] = "grpc"
            p["grpc-opts"] = {"grpc-service-name": j.get("path") or ""}
        elif net in ("h2", "http"):
            p["network"] = "h2"
            if j.get("host"):
                p["h2-opts"] = {"host": [j["host"]], "path": j.get("path") or "/"}
        return p
    except Exception:
        return None


def uri_to_clash(link):
    try:
        scheme, rest = link.split("://", 1)
        scheme = scheme.lower()
        frag = ""
        if "#" in rest:
            rest, frag = rest.split("#", 1)
        frag = urllib.parse.unquote(frag)

        if scheme == "ss":
            if "@" not in rest:
                dec = b64d(rest).decode("utf-8", "ignore")
                if ":" not in dec or "@" not in dec.split(":", 1)[1]:
                    return None
                method, rest2 = dec.split(":", 1)
                pw, hp = rest2.split("@", 1)
            else:
                userinfo, hp = rest.split("@", 1)
                try:
                    method, pw = b64d(userinfo).decode("utf-8", "ignore").split(":", 1)
                except Exception:
                    if ":" not in userinfo:
                        return None
                    method, pw = userinfo.split(":", 1)
            host = hp.split(":")[0]
            port = int(re.sub(r"\D", "", hp.split(":")[1].split("?")[0]) or 0)
            if not host or not port:
                return None
            return {"name": frag or "ss-%s" % host, "type": "ss", "server": host,
                    "port": port, "cipher": method, "password": pw, "udp": True}

        m = re.match(r"^([^@]+)@([^:/?#]+):(\d+)", rest)
        if not m:
            return None
        userinfo, host, port = m.group(1), m.group(2), int(m.group(3))
        q = urllib.parse.parse_qs(rest.split("?", 1)[1] if "?" in rest else "")

        if scheme in ("vless", "trojan"):
            p = {"name": frag or "%s-%s" % (scheme, host), "type": scheme,
                 "server": host, "port": port, "udp": True}
            if scheme == "vless":
                p["uuid"] = urllib.parse.unquote(userinfo)
            else:
                p["password"] = urllib.parse.unquote(userinfo)
            sec = (_qget(q, "security") or "").lower()
            if sec in ("tls", "reality", "xtls") or scheme == "trojan":
                p["tls"] = True
                p["servername"] = _qget(q, "sni") or _qget(q, "peer") or host
                if _qget(q, "fp"):
                    p["client-fingerprint"] = _qget(q, "fp")
                if sec == "reality":
                    p["reality-opts"] = {"public-key": _qget(q, "pbk") or "",
                                         "short-id": _qget(q, "sid") or ""}
            net = (_qget(q, "type") or "tcp").lower()
            if net == "ws":
                p["network"] = "ws"
                p["ws-opts"] = {"path": urllib.parse.unquote(_qget(q, "path") or "/")}
                if _qget(q, "host"):
                    p["ws-opts"]["headers"] = {"Host": _qget(q, "host")}
            elif net == "grpc":
                p["network"] = "grpc"
                p["grpc-opts"] = {"grpc-service-name": _qget(q, "serviceName") or ""}
            return p

        if scheme in ("hysteria2", "hy2", "hysteria"):
            p = {"name": frag or "hy2-%s" % host, "type": "hysteria2", "server": host,
                 "port": port, "password": urllib.parse.unquote(userinfo), "udp": True}
            if _qget(q, "sni"):
                p["sni"] = _qget(q, "sni")
            if _qget(q, "insecure") == "1":
                p["skip-cert-verify"] = True
            return p
    except Exception:
        return None
    return None


# ---------------- 上游解析 ----------------

def parse_any(raw):
    """返回 (links, clash_proxies)"""
    text = raw.decode("utf-8", "ignore").strip()
    links, proxies = [], []

    try:
        dec = b64d(text).decode("utf-8", "ignore")
        if "://" in dec:
            text = dec
    except Exception:
        pass

    if re.search(r"^\s*proxies\s*:", text, re.M):
        try:
            import yaml
            data = yaml.safe_load(text) or {}
            for p in (data.get("proxies") or []):
                if isinstance(p, dict) and p.get("type"):
                    proxies.append(p)
            if proxies:
                return links, proxies
        except Exception as e:
            print("  [warn] clash 解析失败: %s" % e)

    for line in text.splitlines():
        line = line.strip()
        if LINK_RE.match(line):
            links.append(line)
    return links, proxies


def dedup(seq, key=None):
    seen, out = set(), []
    for x in seq:
        k = key(x) if key else x
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


# ---------------- 主流程 ----------------

def main():
    raw_src = os.environ.get("SUB_SOURCES", "").strip()
    if raw_src:
        try:
            sources = json.loads(raw_src)
            if isinstance(sources, str):
                sources = [sources]
        except Exception:
            sources = [s.strip() for s in raw_src.splitlines() if s.strip()]
        origin = "SUB_SOURCES"
    else:
        sources = list(DEFAULT_SOURCES)
        origin = "内置默认源"
    print("[sync-hub] 源来自: %s (%d 个)" % (origin, len(sources)))

    all_links, all_proxies = [], []
    for i, url in enumerate(sources, 1):
        try:
            l, p = parse_any(fetch(url))
            print("  [%d/%d] %s -> links=%d proxies=%d" % (i, len(sources), url[:56], len(l), len(p)))
            all_links += l
            all_proxies += p
        except Exception as e:
            print("  [%d/%d] 拉取失败: %s" % (i, len(sources), e))

    all_links = dedup(all_links)
    all_proxies = dedup(all_proxies, key=lambda p: (p.get("server"), p.get("port"), p.get("type")))

    # 明文链接 -> Clash 节点
    converted = []
    for l in all_links:
        p = vmess_to_clash(l) if l.lower().startswith("vmess://") else uri_to_clash(l)
        if p and p.get("server") and p.get("port"):
            converted.append(p)
    merged = dedup(all_proxies + converted,
                   key=lambda p: (p.get("server"), p.get("port"), p.get("type")))

    # 节点名清洗 + 唯一化
    seen, nodes = set(), []
    for i, p in enumerate(merged):
        n = (p.get("name") or "node-%d" % i).strip().replace("\n", " ").replace('"', "'")[:42]
        if not n:
            n = "node-%d" % i
        if n in seen:
            n = "%s#%d" % (n, i)
        seen.add(n)
        p["name"] = n
        nodes.append(p)

    if all_links:
        (OUT / "v2ray.txt").write_text(
            base64.b64encode("\n".join(all_links).encode()).decode(), encoding="utf-8")

    if nodes:
        import yaml
        cfg = {"port": 7890, "socks-port": 7891, "allow-lan": False, "mode": "rule",
               "log-level": "info", "proxies": nodes,
               "proxy-groups": [{"name": "PROXY", "type": "select",
                                 "proxies": [p["name"] for p in nodes] + ["DIRECT"]}],
               "rules": ["MATCH,PROXY"]}
        (OUT / "clash.yaml").write_text(
            yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")

    print("[sync-hub] 完成: 链接 %d 条 | Clash 节点 %d 个" % (len(all_links), len(nodes)))
    print("[sync-hub] 类型分布: %s" % dict(Counter(p["type"] for p in nodes)))
    return 0


if __name__ == "__main__":
    sys.exit(main())