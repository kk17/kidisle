#!/usr/bin/env python3
"""kidisle 打标结果合并校验器（stage 3，子 agent 流）。

把若干打标 chunk JSON（打标子 agent 的产出）合并成 data/tagged.json，
逐条过 schema 校验（枚举、字段类型），非法条目丢弃并报告。

chunk 文件格式（打标 agent 的输出）：JSON 数组，元素形如
    {"bvid":"...","suitable":true,"age":["3-6"],"language":["zh"],"theme":["science"],"note":"..."}

用法：
    python3 scripts/merge_tags.py chunk1.json chunk2.json ...
    python3 scripts/merge_tags.py /tmp/kidisle-research/tags-chunk-*.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAXONOMY = json.loads((ROOT / "src/data/taxonomy.json").read_text(encoding="utf-8"))
ALLOWED = {
    "age": {t["id"] for t in TAXONOMY["age_bands"]},
    "language": {t["id"] for t in TAXONOMY["languages"]},
    "theme": {t["id"] for t in TAXONOMY["themes"]},
}


def validate(entry, bvid):
    """校验一条打标；返回规整后的 dict 或 None（丢弃）。"""
    if not isinstance(entry, dict):
        return None
    if entry.get("bvid") != bvid:
        entry = {**entry, "bvid": bvid}
    suitable = bool(entry.get("suitable"))
    tags = {}
    valid = suitable
    for key, allowed in ALLOWED.items():
        vals = entry.get(key) or []
        if not isinstance(vals, list):
            valid = False
            vals = []
        tags[key] = [v for v in vals if isinstance(v, str) and v in allowed]
    if suitable and any(not tags[k] for k in ALLOWED):
        valid = False  # suitable=true 却缺某个维度 → 判为无效打标
    return {
        "bvid": bvid,
        "suitable": valid,
        "note": str(entry.get("note") or "")[:120],
        "tags": tags,
    }


def main():
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        raise SystemExit("用法: merge_tags.py <chunk.json> ...")
    out_path = ROOT / "data/tagged.json"
    merged = {}
    if out_path.exists():
        for row in json.loads(out_path.read_text(encoding="utf-8"))["videos"]:
            merged[row["bvid"]] = row

    stats = {"in": 0, "valid": 0, "dropped": 0}
    for p in paths:
        try:
            rows = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            print(f"! {p.name}: JSON 解析失败，跳过 ({e})")
            continue
        if isinstance(rows, dict):  # 容忍 {"videos": [...]} 包裹
            rows = rows.get("videos") or rows.get("results") or []
        if not isinstance(rows, list):
            print(f"! {p.name}: 不是数组，跳过")
            continue
        for row in rows:
            stats["in"] += 1
            bvid = row.get("bvid") if isinstance(row, dict) else None
            if not bvid:
                stats["dropped"] += 1
                continue
            entry = validate(row, bvid)
            if entry is None:
                stats["dropped"] += 1
                continue
            stats["valid"] += 1
            merged[bvid] = entry
        print(f"✓ {p.name}: 累计合并 {len(merged)}")

    videos = sorted(merged.values(), key=lambda r: r["bvid"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {"schema_version": 1, "count": len(videos), "videos": videos},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    suitable = sum(1 for v in videos if v["suitable"])
    print(
        f"\n输入 {stats['in']} 条，有效 {stats['valid']}，丢弃 {stats['dropped']}；"
        f"库中 {len(videos)} 条（适宜 {suitable}）→ {out_path}"
    )


if __name__ == "__main__":
    main()
