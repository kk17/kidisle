#!/usr/bin/env python3
"""给 B 站候选补抓播放器所需的 aid/cid，以及所属合集（ugc_season）的完整集数列表。

为什么需要 aid/cid（RIGE-1071）：
  B 站官方 embed 播放器在移动端只拿到 bvid 时，会先调 /x/web-interface/view 反查 cid，
  该接口常被 B 站风控拦截（HTTP 412），播放器随即显示「非常抱歉…无法正常播放」占位图，
  登录 B 站也无效。embed URL 直接带上 aid+cid 即可跳过这一步正常播放。

为什么需要合集：
  很多儿童系列是「合集」（每集一个独立 BV 号），而不是「多 P」（一个 BV 多个分 P）。
  原来只抓了多 P 的 pages，合集视频在详情页看不到其他集。

产出：
  - data/candidates*.json：B 站条目补 aid / cid / season{id,title}；多 P 的 pages 每项补 cid
  - data/seasons.json：{season_id: {id, title, up, episodes:[{bvid,aid,cid,title,duration}]}}

用视频页 __INITIAL_STATE__.videoData（同 backfill_pages.py），串行 + 间隔，可断点续跑
（已有 cid 的条目跳过）。默认只处理已发布（src/data/videos.json）的条目。

用法：
    python3 scripts/backfill_embed.py                 # 已发布的 B 站条目
    python3 scripts/backfill_embed.py --all           # 全部候选
    python3 scripts/backfill_embed.py --limit 100     # 本次最多请求 100 条（分批跑）
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backfill_pages import fetch_state  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SEASONS_PATH = ROOT / "data/seasons.json"
MAX_EPISODES = 300  # 单个合集封顶，防止超大合集撑爆快照


def season_from(vd):
    s = vd.get("ugc_season")
    if not s:
        return None
    eps = []
    for sec in s.get("sections") or []:
        for e in sec.get("episodes") or []:
            if not e.get("bvid") or not e.get("cid"):
                continue
            eps.append({
                "bvid": e["bvid"],
                "aid": e.get("aid"),
                "cid": e["cid"],
                "title": (e.get("title") or "")[:80],
                "duration": (e.get("arc") or {}).get("duration") or 0,
            })
    if len(eps) < 2:
        return None
    return {
        "id": s["id"],
        "title": (s.get("title") or "")[:80],
        "up": (vd.get("owner") or {}).get("name") or "",
        "episodes": eps[:MAX_EPISODES],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="处理全部候选，而不只是已发布条目")
    ap.add_argument("--limit", type=int, default=0, help="本次最多请求条数（0=不限）")
    ap.add_argument("--sleep", type=float, default=1.5)
    args = ap.parse_args()

    published = None
    if not args.all:
        vids = json.loads((ROOT / "src/data/videos.json").read_text(encoding="utf-8"))["videos"]
        published = {v["bvid"] for v in vids if v.get("bvid")}

    seasons = json.loads(SEASONS_PATH.read_text(encoding="utf-8")) if SEASONS_PATH.exists() else {}
    n_req = 0
    stop = False
    for path in sorted((ROOT / "data").glob("candidates*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        todo = [
            v for v in d["videos"]
            if v.get("bvid") and v.get("source") != "youtube" and v.get("_platform") != "youtube"
            and "cid" not in v and (published is None or v["bvid"] in published)
        ]
        if not todo:
            continue
        print(f"{path.name}: {len(todo)} 条待补")
        dirty = 0
        for v in todo:
            if args.limit and n_req >= args.limit:
                stop = True
                break
            try:
                vd = fetch_state(v["bvid"])
            except Exception as e:  # 网络/风控：跳过，下次续跑
                print(f"  ! {v['bvid']}: {e}")
                vd = None
            n_req += 1
            if vd and vd.get("cid"):
                v["aid"] = vd.get("aid")
                v["cid"] = vd.get("cid")
                cids = {pg.get("page"): pg.get("cid") for pg in vd.get("pages") or []}
                for pg in v.get("pages") or []:
                    if cids.get(pg.get("page")):
                        pg["cid"] = cids[pg["page"]]
                s = season_from(vd)
                if s:
                    seasons[str(s["id"])] = s
                    v["season"] = {"id": s["id"], "title": s["title"]}
                else:
                    v["season"] = None
                dirty += 1
                print(f"  ✓ {v['bvid']} cid={v['cid']}" + (f" 合集《{s['title']}》{len(s['episodes'])} 集" if s else ""))
            elif vd is not None:
                v["cid"] = None  # 视频页无 cid（已失效/下架），标记已处理
                print(f"  ✗ {v['bvid']} 无 cid（可能已失效）")
                dirty += 1
            if dirty and dirty % 20 == 0:
                path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
                SEASONS_PATH.write_text(json.dumps(seasons, ensure_ascii=False, indent=1), encoding="utf-8")
            time.sleep(args.sleep)
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        SEASONS_PATH.write_text(json.dumps(seasons, ensure_ascii=False, indent=1), encoding="utf-8")
        if stop:
            break
    print(f"完成，本次 {n_req} 次请求，合集 {len(seasons)} 个")


if __name__ == "__main__":
    main()
