#!/usr/bin/env python3
"""给候选池里缺头像（up_face）的博主补抓头像。

每个缺头像的博主取其一条视频页，从 __INITIAL_STATE__.videoData.owner.face 提取。
2.5s 间隔，串行，量级 = 博主数（~60-100 次请求）。

用法：python3 scripts/backfill_faces.py
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


def fetch_face(bvid):
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
    if not m:
        return None
    owner = (json.loads(m.group(1)).get("videoData") or {}).get("owner") or {}
    return owner.get("face")


def main():
    n_req = 0
    for path in (ROOT / "data/candidates.json", ROOT / "data/candidates-b.json"):
        if not path.exists():
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        videos = d["videos"]
        # 博主 -> 首个有标题的 bvid
        first_bvid = {}
        for v in videos:
            up = v.get("up")
            if up and up not in first_bvid and v.get("title"):
                first_bvid[up] = v["bvid"]
        todo = [up for up, bv in first_bvid.items()
                if not any(x.get("up") == up and x.get("up_face") for x in videos)]
        print(f"{path.name}: {len(todo)} 位博主缺头像")
        for up in todo:
            bv = first_bvid[up]
            try:
                face = fetch_face(bv)
                n_req += 1
            except Exception as e:
                print(f"  ! {up}: {e}")
                face = None
            if face:
                for v in videos:
                    if v.get("up") == up:
                        v["up_face"] = face
                print(f"  ✓ {up}")
            time.sleep(2.5)
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完成，共 {n_req} 次请求")


if __name__ == "__main__":
    main()
