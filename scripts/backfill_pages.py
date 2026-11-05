#!/usr/bin/env python3
"""给候选池里缺分 P 列表（pages 字段缺失，非空）的条目补抓。

用视频页 __INITIAL_STATE__.videoData.pages 提取（封顶 100 集），
只处理"多 P"视频（单 P 不存）。2.5s 间隔串行。

用法：python3 scripts/backfill_pages.py
"""

import gzip
import json
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def fetch_state(bvid):
    req = urllib.request.Request(
        f"https://www.bilibili.com/video/{bvid}",
        headers={"User-Agent": UA, "Accept-Encoding": "gzip", "Referer": "https://www.bilibili.com/"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    html = data.decode("utf-8", "ignore")
    m = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*</script>", html, re.S) or re.search(
        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});\s*\(function", html, re.S
    )
    return json.loads(m.group(1)).get("videoData") if m else None


def main():
    n_req = 0
    for path in sorted((ROOT / "data").glob("candidates*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        videos = d["videos"]
        todo = [v for v in videos if v.get("title") and "pages" not in v]
        if not todo:
            print(f"{path.name}: 无需补抓")
            continue
        print(f"{path.name}: {len(todo)} 条缺分 P 数据")
        for v in todo:
            try:
                vd = fetch_state(v["bvid"])
                n_req += 1
            except Exception as e:
                print(f"  ! {v['bvid']}: {e}")
                vd = None
            if vd:
                raw = vd.get("pages") or []
                if len(raw) > 1:
                    v["total_pages"] = vd.get("videos")
                    v["pages"] = [
                        {"page": pg.get("page"), "part": (pg.get("part") or "")[:80], "duration": pg.get("duration")}
                        for pg in raw[:100]
                    ]
                    print(f"  ✓ {v['bvid']} {len(raw)} 集")
                else:
                    v["pages"] = []  # 单 P，标记为已处理
            time.sleep(2.5)
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成，共 {n_req} 次请求")


if __name__ == "__main__":
    main()
