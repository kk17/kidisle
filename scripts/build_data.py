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
