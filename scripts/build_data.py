#!/usr/bin/env python3
"""tinycove 数据发布脚本（stage 3 → 站点之间的桥）。

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
import re
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 已知精选来源的原文链接（调研报告 docs/data-sources.md）
SOURCE_URLS = {
    "小花生宝藏UP主盘点": "https://www.163.com/dy/article/HIJ32IVO05268AGI.html",
    "外滩教育推荐": "https://www.thepaper.cn/newsDetail_forward_19093414",
}

# 打标 note 里的管线备注（枚举缺口时期的「暂归/建议增设/枚举无」）不面向家长，
# 发布前剥掉。句式为 build_books.py PIPELINE_NOTE_RE 的超集（图书侧目前只有
# 「建议增设…主题」句式）；只吞前或后一个分隔符，避免剥句中备注时粘连两段。
_NOTE_CORE = (
    r"建议增设(?:人文|体育|语文)(?:主题)?[了]?"
    r"|(?:语文|人文|体育)(?:启蒙)?(?:类|历史)?(?:暂归|类归|归)(?:story|life)(?:主题)?"
    r"|枚举无(?:体育|人文|语文)(?:归|暂归)(?:story|life)(?:主题)?"
)
PIPELINE_NOTE_RE = re.compile(
    rf"(?:[,，;；、]\s*(?:{_NOTE_CORE})|(?:{_NOTE_CORE})\s*[,，;；、]|(?:{_NOTE_CORE}))"
)


def _clean_note(note: str) -> str:
    note = PIPELINE_NOTE_RE.sub("", note)
    # 剥离后相邻分隔符合并，再去头尾
    note = re.sub(r"([,，;；、])\s*[,，;；、\s]+", r"\1", note)
    return note.strip(" ，,;；、\t")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tagged", type=Path, default=ROOT / "data/tagged.json")
    ap.add_argument("--out", type=Path, default=ROOT / "src/data/videos.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-per-channel", type=int, default=6,
                    help="单个 UP 主/频道最多收录多少条，防止高频系列刷屏")
    args = ap.parse_args()

    tagged = json.loads(args.tagged.read_text(encoding="utf-8"))["videos"]
    suitable = [t for t in tagged if t.get("suitable")]
    print(f"打标 {len(tagged)} 条，适宜 {len(suitable)} 条")

    # 合并全部候选池（多批次采集，含 YouTube），供元数据回填
    # key：B站=bvid，YouTube=vid（统一"视频键"）
    pool = {}
    for p in sorted((ROOT / "data").glob("candidates*.json")):
        for v in json.loads(p.read_text(encoding="utf-8"))["videos"]:
            key = v.get("bvid") or v.get("vid")
            if key:
                v["_key"] = key
                pool.setdefault(key, v)

    # 保留已发布条目的 added_at（重跑管线不应把所有视频都刷成"今天新增"）
    prev_added = {}
    if args.out.exists():
        for v in json.loads(args.out.read_text(encoding="utf-8")).get("videos", []):
            prev_added[v["id"]] = v.get("added_at")

    videos = []
    for t in suitable:
        cand = pool.get(t["bvid"])
        if not cand:
            print(f"  ! 候选池缺元数据，跳过 {t['bvid']}")
            continue
        langs = t["tags"]["language"] or ["zh"]
        is_yt = cand.get("_platform") == "youtube" or cand.get("source") == "youtube"
        entry_id = ("yt-" + t["bvid"]) if is_yt else ("bv-" + t["bvid"].lower()[2:])
        entry = {
                "id": entry_id,
                "source": "youtube" if is_yt else "bilibili",
                "bvid": None if is_yt else t["bvid"],
                "vid": t["bvid"] if is_yt else None,
                "title": cand.get("title") or t["bvid"],
                "up": cand.get("up") or "",
                "duration_seconds": cand.get("duration_seconds") or 0,
                "cover": cand.get("cover") or "",
                # embed 播放器需要 aid+cid（只给 bvid 时移动端会被 B 站风控 412，RIGE-1071）
                "aid": None if is_yt else cand.get("aid"),
                "cid": None if is_yt else cand.get("cid"),
                "season_id": None if is_yt else (cand.get("season") or {}).get("id"),
                "total_pages": cand.get("total_pages") or 0,
                "pages": cand.get("pages") or [],
                "note": _clean_note(t.get("note") or ""),
                "tags": {
                    "age": t["tags"]["age"],
                    "language": langs[:1],
                    "theme": t["tags"]["theme"],
                },
                "added_at": prev_added.get(entry_id) or time.strftime("%Y-%m-%d"),
        }
        videos.append(entry)

    # 单频道配额：同一 UP 主/频道最多 N 条（保留时长较长的代表条目优先），
    # 避免某个高频系列（如宝宝巴士 17 条）淹没其他来源
    by_channel = {}
    for v in videos:
        by_channel.setdefault(v["up"] or "未知UP主", []).append(v)
    trimmed = 0
    if args.max_per_channel > 0:
        keep = []
        for up, vs in by_channel.items():
            if len(vs) > args.max_per_channel:
                # 取时长最长的 N 条作为代表（长内容通常信息量更足），其余裁撤
                vs = sorted(vs, key=lambda v: -(v.get("duration_seconds") or 0))[: args.max_per_channel]
                trimmed += len(by_channel[up]) - len(vs)
            keep.extend(vs)
        videos = keep
    if trimmed:
        print(f"单频道配额（≤{args.max_per_channel} 条）裁撤 {trimmed} 条")

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
    taxo = json.loads((ROOT / "src/data/taxonomy.json").read_text(encoding="utf-8"))
    theme_labels = {t["id"]: t["label"] for t in taxo["themes"]}
    theme_labels_en = {t["id"]: t["label_en"] for t in taxo["themes"]}
    by_up = {}
    for v in videos:
        by_up.setdefault(v["up"] or "未知UP主", []).append(v)
    bloggers = []
    for up, vids in by_up.items():
        def _vidkey(x):
            return x.get("bvid") or x.get("vid")
        face = next((pool.get(_vidkey(v), {}).get("up_face") for v in vids
                     if pool.get(_vidkey(v), {}).get("up_face")), "")
        mid = next((pool.get(_vidkey(v), {}).get("mid") for v in vids
                    if pool.get(_vidkey(v), {}).get("mid")), None)
        themes = [t for v in vids for t in v["tags"]["theme"]]
        top_themes = [theme_labels[t] for t, _ in Counter(themes).most_common(2)]
        top_themes_en = [theme_labels_en[t] for t, _ in Counter(themes).most_common(2)]
        info = overlay.get(up, {})
        source_name = info.get("source") or "社区精选"
        source_url = info.get("source_url") or SOURCE_URLS.get(source_name, "")
        # 推荐理由：手工覆盖层优先；否则按主题分布自动生成中英两版
        reason_zh = info.get("reason") or (
            f"收录 {len(vids)} 条视频，主打{'、'.join(top_themes)}" if top_themes
            else f"收录 {len(vids)} 条视频"
        )
        reason_en = info.get("reason_en") or (
            f"{len(vids)} videos, mainly {' and '.join(top_themes_en)}" if top_themes_en
            else f"{len(vids)} videos"
        )
        bloggers.append({
            "up": up,
            "avatar": face,
            "video_count": len(vids),
            "themes": [t for t, _ in Counter(themes).most_common(3)],
            "platforms": sorted({v.get("source") or "bilibili" for v in vids}),
            "reason": reason_zh,
            "reason_en": reason_en,
            "source": source_name,
            "source_url": source_url,
            "mid": mid,
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

    # ---- 合集（ugc_season）：只发布被收录视频引用到的合集，供详情页「合集选集」面板 ----
    seasons_src = ROOT / "data/seasons.json"
    all_seasons = json.loads(seasons_src.read_text(encoding="utf-8")) if seasons_src.exists() else {}
    used = {str(v["season_id"]) for v in videos if v.get("season_id")}
    seasons_out = {k: all_seasons[k] for k in sorted(used) if k in all_seasons}
    (ROOT / "src/data/seasons.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "note": "由 scripts/build_data.py 从 data/seasons.json（scripts/backfill_embed.py 抓取）生成，请勿手工编辑。",
                "seasons": seasons_out,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"合集 {len(seasons_out)} 个")

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
