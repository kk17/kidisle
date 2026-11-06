#!/usr/bin/env python3
"""kidisle YouTube 采集（英文区）。

从精选清单 data/curated/yt-links-*.md 提取 vid，用 oEmbed 补全标题/频道，
缩略图用 i.ytimg.com 固定地址，产出 data/candidates-y.json。

用法：python3 scripts/collect_yt.py
"""

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
VID_RE = re.compile(r"[A-Za-z0-9_-]{11}")


def oembed(vid):
    url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="只处理匹配的文件名片段，如 wx")
    ap.add_argument("--out", default="candidates-y.json")
    args = ap.parse_args()

    pool = {}
    theme_hint = {}
    files = [f for f in sorted((ROOT / "data/curated").glob("yt-links-*.md"))
             if args.only in f.name]
    for md in files:
        for line in md.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            parts = [x.strip() for x in line.split("|")]
            m = VID_RE.fullmatch(parts[0]) if parts else None
            if not m:
                # 行内可能混有 URL，尝试从任意段提取 vid
                for seg in parts:
                    vm = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", seg)
                    if vm:
                        parts[0] = vm.group(1)
                        break
            vid = parts[0]
            if not VID_RE.fullmatch(vid):
                continue
            channel = parts[1] if len(parts) > 1 else ""
            title_hint = parts[2] if len(parts) > 2 else ""
            theme_hint[vid] = parts[3] if len(parts) > 3 else ""
            if vid not in pool:
                pool[vid] = {
                    "vid": vid,
                    "source": "youtube",
                    "title": title_hint,
                    "up": channel,
                    "cover": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                    "desc": "",
                    "duration_seconds": 0,
                    "source_ref": md.name,
                }

    print(f"精选清单提取 {len(pool)} 个 vid，oEmbed 富化中…")
    enriched = 0
    for vid, item in pool.items():
        try:
            data = oembed(vid)
            item["title"] = data.get("title") or item["title"]
            item["up"] = data.get("author_name") or item["up"]
            enriched += 1
        except Exception as e:
            print(f"  ! oEmbed 失败 {vid}: {e}")
        time.sleep(1.0)

    # 主题线索并进 desc（打标 agent 需要）
    for vid, item in pool.items():
        hint = theme_hint.get(vid)
        if hint:
            item["desc"] = f"[topic hint: {hint}]"

    out = ROOT / "data" / args.out
    out.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "count": len(pool),
                "videos": sorted(pool.values(), key=lambda v: v["vid"]),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"完成：{len(pool)} 条（oEmbed 成功 {enriched}）→ {out}")


if __name__ == "__main__":
    main()
