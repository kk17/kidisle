#!/usr/bin/env python3
"""补抓 YouTube 频道头像。

对 candidates-y.json 里缺 up_face 的频道：oEmbed 拿 author_url（频道页），
抓频道页 HTML 提取 og:image（即频道头像），失败则回退 unavatar.io 代理。
"""

import gzip
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def oembed_author_url(vid):
    url = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"}
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8")).get("author_url")


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data.decode("utf-8", "ignore")


def channel_avatar(author_url):
    html = fetch_text(author_url)
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if m and m.group(1):
        return m.group(1)
    m = re.search(r'"avatar":\{"thumbnails":\[\{"url":"([^"]+)"', html)
    return m.group(1) if m else None


def main():
    path = ROOT / "data/candidates-y.json"
    d = json.loads(path.read_text(encoding="utf-8"))
    videos = d["videos"]
    by_up = {}
    for v in videos:
        if v.get("up"):
            by_up.setdefault(v["up"], []).append(v)
    todo = [up for up, vs in by_up.items() if not any(x.get("up_face") for x in vs)]
    print(f"{len(todo)} 个 YouTube 频道缺头像")
    for up in todo:
        vid = next(v["vid"] for v in by_up[up])
        face = None
        try:
            author_url = oembed_author_url(vid)
            if author_url:
                face = channel_avatar(author_url)
        except Exception as e:
            print(f"  ! {up}: 频道页失败 {e}")
        if not face:
            slug = up.replace("@", "").replace(" ", "")
            face = f"https://unavatar.io/youtube/{urllib.parse.quote(slug)}"
            print(f"  ~ {up}: 回退 unavatar")
        else:
            print(f"  ✓ {up}")
        for v in by_up[up]:
            v["up_face"] = face
        time.sleep(1.5)
    path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("完成")


if __name__ == "__main__":
    main()
