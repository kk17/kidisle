#!/usr/bin/env python3
"""kidisle 采集脚本（stage 2）。

从 B 站公开 API 采集候选视频元数据，产出原始候选池 candidates.json。
过滤与打标由 stage 3 的 tag.py 完成，这里不做内容判断。

用法：
    python3 scripts/collect.py collect --config scripts/seeds.json --out data/candidates.json
    python3 scripts/collect.py search --keyword "儿童科普" --pages 2
    python3 scripts/collect.py resolve --name "无穷小亮的科普日常"

设计要点：
- 仅请求公开 API（搜索/空间/视频详情），不登录、不抓视频内容；
- 搜索与空间接口需要 wbi 签名（nav 接口取 key + mixin 表排序 + md5）；
- 请求间隔默认 2s，控制对 B 站的礼貌性。
"""

import argparse
import gzip
import hashlib
import json
import os
import urllib.error
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
SEARCH_URL = "https://api.bilibili.com/x/web-interface/wbi/search/type"
SPACE_URL = "https://api.bilibili.com/x/space/wbi/arc/search"
VIEW_URL = "https://api.bilibili.com/x/web-interface/view"

# wbi 签名用 mixin 表（社区公开算法，顺序固定）
MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]

_req_count = 0


def http_get_json(url: str, params: dict = None, cookies: str = "", allow_codes=(0,)) -> dict:
    """GET 并解析 JSON；code 不在 allow_codes 时抛 RuntimeError。"""
    global _req_count
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    payload = None
    for attempt in range(3):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Cookie": cookies,
                "Referer": "https://www.bilibili.com/",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code in (412, 429) and attempt < 2:
                time.sleep(4 * (attempt + 1))  # 风控抖动，退避重试
                continue
            raise RuntimeError(f"HTTP {e.code} url={url}") from e
    _req_count += 1
    if payload.get("code") not in allow_codes:
        raise RuntimeError(f"API code={payload.get('code')} msg={payload.get('message')!r} url={url}")
    return payload.get("data", {})


class BilibiliClient:
    def __init__(self, delay: float = 2.0, sessdata: str = ""):
        self.delay = delay
        # 匿名 buvid3：从 finger/spi 取真实值；搜索/空间接口匿名仍会被风控
        # （v_voucher / -352 / -412），配置 SESSDATA 后才解锁发现类接口。
        try:
            spi = http_get_json("https://api.bilibili.com/x/frontend/finger/spi")
            self.cookies = f"buvid3={spi['b_3']};buvid4={spi['b_4']}"
        except Exception:
            self.cookies = f"buvid3={hashlib.md5(str(time.time()).encode()).hexdigest()}"
        if sessdata:
            self.cookies += f";SESSDATA={sessdata}"
        self._wbi_key = None

    def _throttle(self):
        time.sleep(self.delay)

    def wbi_key(self) -> str:
        if self._wbi_key:
            return self._wbi_key
        data = http_get_json(NAV_URL, cookies=self.cookies, allow_codes=(0, -101))["wbi_img"]
        img_key = data["img_url"].rsplit("/", 1)[1].split(".")[0]
        sub_key = data["sub_url"].rsplit("/", 1)[1].split(".")[0]
        raw = img_key + sub_key
        self._wbi_key = "".join(raw[i] for i in MIXIN_KEY_ENC_TAB)[:32]
        return self._wbi_key

    def _signed_params(self, params: dict) -> dict:
        params = {**params, "wts": int(time.time())}
        # 签名要求：按 key 排序、urlencode 过滤掉 !'()*、值做 strips
        filtered = {
            k: "".join(ch for ch in str(v) if ch not in "!'()*").strip()
            for k, v in sorted(params.items())
        }
        query = urllib.parse.urlencode(filtered)
        params["w_rid"] = hashlib.md5((query + self.wbi_key()).encode()).hexdigest()
        return params

    def search_videos(self, keyword, pages=1):
        out = []
        for page in range(1, pages + 1):
            self._throttle()
            data = http_get_json(
                SEARCH_URL,
                self._signed_params(
                    {"search_type": "video", "keyword": keyword, "page": page, "page_size": 30}
                ),
                cookies=self.cookies,
            )
            results = (data.get("result") or []) if isinstance(data, dict) else []
            for r in results:
                if r.get("type") != "video":
                    continue
                out.append(self._search_row(r, source=f"search:{keyword}"))
            if len(results) < 20:
                break
        return out

    def search_user(self, name: str):
        """按名字解析 UP 主，返回 {mid, uname}；找不到返回 None。"""
        self._throttle()
        data = http_get_json(
            SEARCH_URL,
            self._signed_params({"search_type": "bili_user", "keyword": name}),
            cookies=self.cookies,
        )
        for r in data.get("result") or []:
            if r.get("type") == "bili_user" or "mid" in r:
                return {"mid": r["mid"], "uname": r.get("uname") or name}
        return None

    def user_videos(self, mid, name, pages=2):
        out = []
        for page in range(1, pages + 1):
            self._throttle()
            try:
                data = http_get_json(
                    SPACE_URL,
                    self._signed_params(
                        {"mid": mid, "ps": 30, "pn": page, "order": "pubdate"}
                    ),
                    cookies=self.cookies,
                )
            except Exception as e:  # 空间接口对未登录风控较严，失败不致命
                print(f"  ! 空间接口失败 mid={mid} page={page}: {e}", file=sys.stderr)
                break
            vlist = (data.get("list") or {}).get("vlist") or []
            for r in vlist:
                out.append(
                    {
                        "bvid": r.get("bvid"),
                        "title": r.get("title"),
                        "up": name,
                        "mid": mid,
                        "duration": r.get("length"),
                        "pubdate": r.get("created"),
                        "play": r.get("play"),
                        "source": f"user:{name}",
                    }
                )
            if len(vlist) < 30:
                break
        return out

    def enrich(self, bvid):
        """视频详情（含 desc），用于 LLM 打标。失败返回 None。"""
        self._throttle()
        try:
            data = http_get_json(VIEW_URL, {"bvid": bvid})
        except Exception as e:
            print(f"  ! 详情失败 {bvid}: {e}", file=sys.stderr)
            return None
        return {
            "desc": (data.get("desc") or "")[:500],
            "duration_seconds": data.get("duration"),
            "cover": data.get("pic"),
            "pubdate": data.get("pubdate"),
            "view": (data.get("stat") or {}).get("view"),
            "like": (data.get("stat") or {}).get("like"),
        }

    def enrich_html(self, bvid: str):
        """降级通道：抓视频页 HTML 的 __INITIAL_STATE__（api 被风控时用）。"""
        self._throttle()
        url = f"https://www.bilibili.com/video/{bvid}"
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept-Encoding": "gzip",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Referer": "https://www.bilibili.com/",
                },
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            if data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            html = data.decode("utf-8", "ignore")
            m = re.search(
                r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*</script>", html, re.S
            ) or re.search(
                r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*\(function", html, re.S
            )
            if not m:
                print(f"  ! HTML 无 INITIAL_STATE {bvid}", file=sys.stderr)
                return None
            v = json.loads(m.group(1)).get("videoData") or {}
            if not v.get("title"):
                return None
            return {
                "title": v.get("title"),
                "desc": (v.get("desc") or "")[:500],
                "up": (v.get("owner") or {}).get("name"),
                "mid": (v.get("owner") or {}).get("mid"),
                "up_face": (v.get("owner") or {}).get("face"),
                "duration_seconds": v.get("duration"),
                "cover": v.get("pic"),
                "pubdate": v.get("pubdate"),
                "view": (v.get("stat") or {}).get("view"),
                "like": (v.get("stat") or {}).get("like"),
            }
        except Exception as e:
            print(f"  ! HTML 详情失败 {bvid}: {e}", file=sys.stderr)
            return None

    @staticmethod
    def _search_row(r: dict, source: str) -> dict:
        return {
            "bvid": r.get("bvid"),
            "title": re.sub(r"</?em[^>]*>", "", r.get("title") or ""),
            "up": r.get("author"),
            "mid": r.get("mid"),
            "duration": r.get("duration"),  # "MM:SS" 或 "HH:MM:SS"
            "play": r.get("play"),
            "source": source,
        }


def parse_duration(text):
    """"MM:SS" / "HH:MM:SS" / 秒数 → 秒。"""
    if text is None:
        return None
    if isinstance(text, int):
        return text
    parts = [int(p) for p in str(text).split(":")]
    seconds = 0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def collect(config_path, out_path, max_per_source, enrich_limit, via="api"):
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    client = BilibiliClient(
        delay=cfg.get("delay_seconds", 2.0), sessdata=os.environ.get("BILIBILI_SESSDATA", "")
    )
    pool = {}

    def add(items):
        for it in items:
            bvid = it.get("bvid")
            if not bvid:
                continue
            if bvid in pool:
                pool[bvid]["source"] += f";{it['source']}"
            else:
                pool[bvid] = it

    # 1) 精选链接：从任意文本（调研笔记/论坛帖存档）里提取 BV 号。
    #    这是 MVP 的主发现通道——B 站匿名搜索/空间接口均被风控，
    #    发现交给人工精选清单与搜索引擎，B 站 API 只负责补全元数据。
    for lf in cfg.get("curated_files", []):
        text = Path(lf).read_text(encoding="utf-8") if Path(lf).exists() else ""
        bvids = re.findall(r"BV[0-9A-Za-z]{10}", text)
        for i, bvid in enumerate(dict.fromkeys(bvids)):
            if bvid not in pool:
                pool[bvid] = {"bvid": bvid, "source": f"curated:{Path(lf).name}#{i}"}
        print(f"== 精选文件 {lf}: 提取 {len(dict.fromkeys(bvids))} 个 bvid")

    # 2) 种子 UP 主：需要 SESSDATA（匿名空间接口被风控）
    has_sessdata = bool(os.environ.get("BILIBILI_SESSDATA"))
    for name in cfg.get("seed_users", []):
        if not has_sessdata:
            print(f"== 跳过 UP 主 {name}（未配置 BILIBILI_SESSDATA，空间接口不可用）")
            continue
        print(f"== 解析 UP 主: {name}")
        user = client.search_user(name)
        if not user:
            print(f"  ! 未找到，跳过")
            continue
        print(f"  mid={user['mid']} ({user['uname']})")
        add(client.user_videos(user["mid"], user["uname"], pages=cfg.get("user_pages", 2)))

    # 3) 关键词搜索：同样需要 SESSDATA
    for kw in cfg.get("search_queries", []):
        if not has_sessdata:
            print(f"== 跳过搜索 {kw!r}（未配置 BILIBILI_SESSDATA）")
            continue
        print(f"== 搜索: {kw}")
        rows = client.search_videos(kw, pages=cfg.get("search_pages", 1))
        print(f"  {len(rows)} 条")
        add(rows)

    # 4) 截断每个来源的贡献量，避免单一来源霸池
    from collections import Counter

    first_source = Counter()
    keep = {}
    for bvid, item in pool.items():
        src = item["source"].split(";")[0].rsplit("#", 1)[0]
        if first_source[src] < max_per_source:
            first_source[src] += 1
            keep[bvid] = item
    pool = keep

    # 5) 富化（详情含 desc，LLM 打标需要）；view 接口匿名可用
    enriched = 0
    enrich_fn = client.enrich_html if via == "html" else client.enrich
    for bvid, item in pool.items():
        if enriched >= enrich_limit:
            break
        detail = enrich_fn(bvid)
        if detail:
            item.update(detail)
            enriched += 1

    candidates = {
        "schema_version": 1,
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "count": len(pool),
        "videos": sorted(pool.values(), key=lambda v: -(v.get("play") or 0)),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n完成：候选 {len(pool)} 条（富化 {enriched}）→ {out_path}")
    print(f"共发起 {_req_count} 次请求")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="按 seeds.json 采集候选池")
    c.add_argument("--config", type=Path, default=Path("scripts/seeds.json"))
    c.add_argument("--out", type=Path, default=Path("data/candidates.json"))
    c.add_argument("--max-per-source", type=int, default=60)
    c.add_argument("--enrich-limit", type=int, default=300)
    c.add_argument("--via", choices=["api", "html"], default="api", help="富化通道：api=view 接口，html=视频页解析（风控降级用）")

    s = sub.add_parser("search", help="单次搜索调试（需 BILIBILI_SESSDATA）")
    s.add_argument("--keyword", required=True)
    s.add_argument("--pages", type=int, default=1)

    r = sub.add_parser("resolve", help="按名字解析 UP 主 mid（需 BILIBILI_SESSDATA）")
    r.add_argument("--name", required=True)

    args = ap.parse_args()
    sessdata = os.environ.get("BILIBILI_SESSDATA", "")
    if args.cmd == "collect":
        collect(args.config, args.out, args.max_per_source, args.enrich_limit, args.via)
    elif args.cmd == "search":
        client = BilibiliClient(sessdata=sessdata)
        rows = client.search_videos(args.keyword, pages=args.pages)
        print(json.dumps(rows[:5], ensure_ascii=False, indent=2))
        print(f"... 共 {len(rows)} 条")
    elif args.cmd == "resolve":
        client = BilibiliClient(sessdata=sessdata)
        print(json.dumps(client.search_user(args.name), ensure_ascii=False))


if __name__ == "__main__":
    main()
