#!/usr/bin/env python3
"""kidisle 数据发布脚本（stage 3 → 站点之间的桥）。

把 tag.py 的打标结果（data/tagged.json）合入站点数据源 src/data/videos.json：
- 只收录 suitable=true 的条目
- 语言标签只保留一个主语言（打标可能给多个，站点筛选按单选设计）
- 去重、按 added_at 倒序

用法：
    python3 scripts/build_data.py            # tagged.json → videos.json
    python3 scripts/build_data.py --dry-run  # 只打印统计
"""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tagged", type=Path, default=ROOT / "data/tagged.json")
    ap.add_argument("--out", type=Path, default=ROOT / "src/data/videos.json")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tagged = json.loads(args.tagged.read_text(encoding="utf-8"))["videos"]
    suitable = [t for t in tagged if t.get("suitable")]
    print(f"打标 {len(tagged)} 条，适宜 {len(suitable)} 条")

    videos = []
    for t in suitable:
        cand = None  # 从候选池补元数据（title/up/cover 等）
        for p in (ROOT / "data/candidates.json",):
            if p.exists():
                pool = {v["bvid"]: v for v in json.loads(p.read_text(encoding="utf-8"))["videos"]}
                cand = pool.get(t["bvid"])
                break
        if not cand:
            continue
        langs = t["tags"]["language"] or ["zh"]
        videos.append(
            {
                "id": "bv-" + t["bvid"].lower()[2:],
                "source": "bilibili",
                "bvid": t["bvid"],
                "title": cand.get("title") or t["bvid"],
                "up": cand.get("up") or "",
                "duration_seconds": cand.get("duration_seconds") or 0,
                "cover": cand.get("cover") or "",
                "note": t.get("note") or "",
                "tags": {
                    "age": t["tags"]["age"],
                    "language": langs[:1],
                    "theme": t["tags"]["theme"],
                },
                "added_at": time.strftime("%Y-%m-%d"),
            }
        )

    videos.sort(key=lambda v: v["added_at"], reverse=True)
    print(f"待写入 {len(videos)} 条")
    if args.dry_run:
        for v in videos[:5]:
            print(" -", v["bvid"], v["title"][:30], v["tags"])
        return

    # ---- 博主聚合层：头像 / 推荐理由 / 来源 ----
    # 头像取自采集富化的 up_face；推荐理由优先取 data/blogger-notes.json 手工覆盖层，
    # 其余按该博主视频的主题分布自动生成兜底文案。
    overlay = {}
    notes_path = ROOT / "data/blogger-notes.json"
    if notes_path.exists():
        overlay = json.loads(notes_path.read_text(encoding="utf-8")).get("bloggers", {})
    theme_labels = {t["id"]: t["label"] for t in json.loads(
        (ROOT / "src/data/taxonomy.json").read_text(encoding="utf-8"))["themes"]}
    pool = {v["bvid"]: v for p in (ROOT / "data/candidates.json", ROOT / "data/candidates-b.json")
            if p.exists() for v in json.loads(p.read_text(encoding="utf-8"))["videos"]}
    by_up = {}
    for v in videos:
        by_up.setdefault(v["up"] or "未知UP主", []).append(v)
    bloggers = []
    for up, vids in by_up.items():
        face = next((pool[v["bvid"]].get("up_face") for v in vids
                     if pool.get(v["bvid"], {}).get("up_face")), "")
        themes = [t for v in vids for t in v["tags"]["theme"]]
        top_themes = [theme_labels[t] for t, _ in Counter(themes).most_common(2)]
        info = overlay.get(up, {})
        reason = info.get("reason") or (
            f"收录 {len(vids)} 条视频，主打{'、'.join(top_themes)}" if top_themes
            else f"收录 {len(vids)} 条视频"
        )
        bloggers.append({
            "up": up,
            "avatar": face,
            "video_count": len(vids),
            "reason": reason,
            "source": info.get("source") or "社区精选",
        })
    bloggers.sort(key=lambda b: -b["video_count"])
    bloggers_out = ROOT / "src/data/bloggers.json"
    bloggers_out.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "note": "由 scripts/build_data.py 生成，请勿手工编辑；推荐理由覆盖层见 data/blogger-notes.json。",
                "bloggers": bloggers,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    args.out.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "note": "由 scripts/build_data.py 从采集/打标管线生成，请勿手工编辑。",
                "updated_at": time.strftime("%Y-%m-%d"),
                "videos": videos,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"→ {args.out}")


if __name__ == "__main__":
    main()
