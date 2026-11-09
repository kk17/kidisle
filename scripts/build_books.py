#!/usr/bin/env python3
"""kidisle 绘本采集与富化（RIGE-815）。

读 data/curated/book-links-*.md（书名 | 作者 | 豆瓣链接 | 推荐语 | 出处），
经豆瓣 suggest + 详情页富化（评分/ISBN/封面/出版社），产 data/book-candidates.json。

用法：
    python3 scripts/build_books.py --collect          # 采集富化
    python3 scripts/build_books.py --merge            # 合并打标结果 → src/data/books.json
"""

import argparse
import gzip
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

# 中文 → 英文书名映射（知名引进绘本，供 Goodreads 匹配；可在 data/blogger-notes 补）
TITLE_EN_OVERRIDES = {
    "猜猜我有多爱你": "Guess How Much I Love You",
    "好饿的毛毛虫": "The Very Hungry Caterpillar",
    "爷爷一定有办法": "Something from Nothing",
    "大卫，不可以": "No, David!",
    "我爸爸": "My Dad",
    "我妈妈": "My Mum",
    "活了100万次的猫": "The Cat That Lived a Million Times",
    "爱心树": "The Giving Tree",
    "逃家小兔": "The Runaway Bunny",
    "月亮的味道": "A Taste of the Moon",
    "小黑鱼": "Swimmy",
    "田鼠阿佛": "Frederick",
    "彩虹色的花": "The Rainbow Flower",
    "你看起来好像很好吃": "You Look Yummy",
    "母鸡萝丝去散步": "Rosie's Walk",
    "野兽国": "Where the Wild Things Are",
    "蚯蚓的日记": "Diary of a Worm",
    "花婆婆": "Miss Rumphius",
    "石头汤": "Stone Soup",
    "獾的礼物": "Badger's Parting Gifts",
}


# 来源列文本 → 奖项 id（awards.json 与 /award/{id}/ 路由用）
AWARD_MAP = [
    ("goodreads choice awards", "grca"),
    ("caldecott", "caldecott"),
    ("凯特·格林纳威", "greenaway"), ("格林纳威", "greenaway"),
    ("carnegie", "greenaway"), ("卡内基", "greenaway"),
    ("博洛尼亚", "bologna"), ("bologna", "bologna"), ("braw", "bologna"),
    ("德国青少年文学奖", "german"), ("deutscher", "german"), ("德国绘本大奖", "german"),
    ("日本绘本赏", "japan"), ("日本絵本賞", "japan"),
    ("bib", "bib"), ("金苹果", "bib"),
    ("陈伯吹", "chen-bochui"),
    ("信谊", "xinyi"),
    ("丰子恺", "fengzikai"),
]


def parse_award(src_text, year_hint=""):
    """从来源列（和年份提示列）解析奖项 id/名称/年份。"""
    text = f"{src_text} {year_hint}".lower()
    for key, aid in AWARD_MAP:
        if key in text:
            years = re.findall(r"(20\d{2})", f"{year_hint} {src_text}")
            year = int(years[0]) if years else None
            return aid, src_text.strip(), year
    return None, src_text.strip(), None


def book_id(title: str) -> str:
    """中文书名经 ascii 清洗会退化为空串，改用标题 MD5 作稳定 id。"""
    return "bk-" + hashlib.md5(title.encode("utf-8")).hexdigest()[:12]


def fetch(url, mobile=False):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
            if mobile
            else UA
        ),
        "Accept-Encoding": "gzip",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = resp.read()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    return data.decode("utf-8", "ignore")


def suggest(title):
    q = urllib.parse.quote(title)
    try:
        raw = fetch(f"https://book.douban.com/j/subject_suggest?q={q}")
        rows = json.loads(raw)
        for r in rows:
            if r.get("type") == "b":
                return r
    except Exception as e:
        print(f"  ! suggest 失败 {title}: {e}")
    return None


def detail(subject_url):
    html = fetch(subject_url)
    out = {}
    m = re.search(r'rating_num" property="v:average">\s*([\d.]+)\s*</strong>', html)
    out["rating"] = float(m.group(1)) if m else None
    m = re.search(r"ISBN[^<]*</span>\s*([\dX]{10,13})", html)
    out["isbn"] = m.group(1) if m else None
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    out["cover"] = m.group(1) if m else ""
    m = re.search(r"作者</span>:\s*(?:<a[^>]*>([^<]+)</a>|\[?([^\s<]+))", html)
    out["author_detail"] = (m.group(1) or m.group(2)).strip() if m else ""
    m = re.search(r"出版社:</span>\s*<a[^>]*>([^<]+)</a>", html)
    out["publisher"] = m.group(1).strip() if m else ""
    m = re.search(r"出版年:</span>\s*([\d-]+)", html)
    out["pub_year"] = m.group(1)[:4] if m else ""
    m = re.search(r'<div class="intro">\s*<p[^>]*>(.*?)</p>', html, re.S)
    if m:
        out["desc"] = re.sub(r"<[^>]+>|\s+", " ", m.group(1)).strip()[:300]
    return out


def goodreads_url(book):
    """ISBN 优先；否则英文名搜索页（搜索页总是可达，等价于可回链）。"""
    if book.get("isbn"):
        return "https://www.goodreads.com/search?q=" + book["isbn"]
    en = book.get("title_en") or TITLE_EN_OVERRIDES.get(book.get("title", ""), "")
    if en:
        return "https://www.goodreads.com/search?q=" + urllib.parse.quote(en)
    return ""


def collect():
    pool = {}
    for md in sorted((ROOT / "data/curated").glob("book-links-*.md")):
        for line in md.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.count("|") < 4:
                continue
            title, author, link, blurb, src = [x.strip() for x in line.split("|", 4)]
            title = title.lstrip("- ").strip()  # 剥掉 Markdown 列表符
            is_gr = "goodreads.com" in link
            is_douban = "douban.com/subject/" in link
            douban_url = link if is_douban else ""
            gr_url = link if is_gr else ""
            if title in pool:
                if gr_url and not pool[title].get("goodreads_url"):
                    pool[title]["goodreads_url"] = gr_url
                if aid and not pool[title].get("award_id"):
                    pool[title]["award_id"] = aid
                    pool[title]["award_year"] = aid_year
                pool[title]["sources"].append({"name": src, "url": link if link.startswith("http") else ""})
                continue
            aid, aid_name, aid_year = parse_award(src, blurb)
            pool[title] = {
                "title": title,
                "author": author,
                "douban_url": douban_url,
                "goodreads_url": gr_url,
                "blurb": blurb,
                "is_en_listed": is_gr,
                "award_id": aid,
                "award_name": aid_name,
                "award_year": aid_year,
                "sources": [{"name": src, "url": link if link.startswith("http") else ""}],
            }
    print(f"清单解析 {len(pool)} 本，豆瓣富化中…")
    n = 0
    for title, b in pool.items():
        if not b["douban_url"]:
            hit = suggest(title)  # 英文书也试豆瓣（常见引进版有中文条目）
            if hit:
                b["douban_url"] = hit["url"]
                b["cover"] = hit.get("pic", "").replace("/s/", "/l/")
                b["author"] = b["author"] or hit.get("author_name", "")
        if b["douban_url"] and not b.get("isbn"):
            try:
                d = detail(b["douban_url"])
                b.update({k: v for k, v in d.items() if v})
                n += 1
            except Exception as e:
                print(f"  ! 详情失败 {title}: {e}")
        b["sources"] = [x for x in b["sources"] if x.get("url")] or b["sources"]
        time.sleep(2.0)
    out = ROOT / "data/book-candidates.json"
    out.write_text(
        json.dumps({"schema_version": 1, "count": len(pool), "books": list(pool.values())},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"完成：{len(pool)} 本（详情成功 {n}）→ {out}")


def ol_search_cover(title, author):
    """Open Library 搜索 + 封面（英文书豆瓣无条目时的封面兜底）。"""
    # 作者字段经豆瓣富化常带中文（如 "Vera Brosgol 文/图"），OL 只认 ASCII
    author_ascii = re.sub(r"[^\x20-\x7e]", "", author or "").strip()
    params = {"title": title, "limit": 1, "fields": "cover_i"}
    if author_ascii:
        params["author"] = author_ascii
    q = urllib.parse.urlencode(params)
    raw = fetch(f"https://openlibrary.org/search.json?{q}")
    docs = json.loads(raw).get("docs") or []
    if docs and docs[0].get("cover_i"):
        return f"https://covers.openlibrary.org/b/id/{docs[0]['cover_i']}-L.jpg"
    return ""


def covers():
    """把豆瓣封面下载到 public/covers/（豆瓣图床对无 Referer 热链返回 418，
    浏览器端无法伪造 Referer，故构建时自托管）。"""
    cands = json.loads((ROOT / "data/book-candidates.json").read_text(encoding="utf-8"))["books"]
    out_dir = ROOT / "public/covers"
    out_dir.mkdir(parents=True, exist_ok=True)
    done = fail = 0
    for b in cands:
        bid = book_id(b["title"])
        local = out_dir / f"{bid}.jpg"
        if local.exists():
            continue
        url = b.get("cover") or ""
        if not url and b.get("isbn"):
            # 有 ISBN：Open Library 封面接口直接按 ISBN 取
            url = f"https://covers.openlibrary.org/b/isbn/{b['isbn']}-L.jpg"
            b["cover"] = url
        if not url:
            # 英文书豆瓣无条目：Open Library 搜索兜底
            try:
                url = ol_search_cover(b["title"], b.get("author") or "")
                if url:
                    b["cover"] = url
            except Exception as e:
                print(f"  ! OpenLibrary 失败 {b['title']}: {e}")
                continue
        if not url:
            continue
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Referer": "https://book.douban.com/",
                "Accept-Encoding": "gzip",
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            if data[:2] == b"\xff\xd8" and len(data) > 2000:
                local.write_bytes(data)
                done += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  ! 封面失败 {b['title']}: {e}")
            fail += 1
        time.sleep(0.6)
    print(f"封面下载：成功 {done}，失败 {fail} → {out_dir}")


# 图书主题迁移：打标用的是视频主题枚举，发布时迁移到图书专属枚举
BOOK_THEME_MAP = {
    "story": "stories", "social": "emotions", "science": "knowledge",
    "nature": "nature", "math": "math", "english": "english",
    "life": "habits", "music": "art", "craft": "art", "animation": "stories",
}
# 打标时被迫暂归 story 且 reason 注明的人文/国学/历史类 → 语言人文
HUMANITIES_MARK = ("人文", "语文", "古诗", "历史", "民俗", "国学", "汉语")
# 管线产物注释不面向家长，展示前剥掉
PIPELINE_NOTE_RE = re.compile(r"[,，;；、\s]*建议增设(人文|体育|语文)主题[了]?[,，;；、]?\s*")


def migrate_book_themes(tags, reason):
    """视频主题枚举 → 图书主题枚举；人文标记升级为 literacy。"""
    humanities = any(k in reason for k in HUMANITIES_MARK)
    out = []
    for t in tags.get("theme", []):
        if t == "story" and humanities:
            tid = "literacy"
        else:
            tid = BOOK_THEME_MAP.get(t, "stories")
        if tid not in out:
            out.append(tid)
    return out[:3]


def clean_reason(reason):
    return PIPELINE_NOTE_RE.sub("", reason).strip(" ,，;；、")


def merge():
    """合并 book-tagged.json（打标结果）→ src/data/books.json。"""
    cands = json.loads((ROOT / "data/book-candidates.json").read_text(encoding="utf-8"))["books"]
    tagged_path = ROOT / "data/book-tagged.json"
    tagged = {t["title"]: t for t in json.loads(tagged_path.read_text(encoding="utf-8"))["books"]} \
        if tagged_path.exists() else {}

    taxo = json.loads((ROOT / "src/data/taxonomy.json").read_text(encoding="utf-8"))
    theme_en = {t["id"]: t["label_en"] for t in taxo["themes"]}

    books = []
    skipped = 0
    for b in cands:
        t = tagged.get(b["title"])
        if not t:
            skipped += 1
            continue
        if not t.get("suitable"):
            continue
        t = tagged.get(b["title"])
        # 平台判定：collect_yt 产出的候选带 vid，B站候选带 bvid
        is_yt = "vid" in b or b.get("source") == "youtube"
        # 视频主题 → 图书主题迁移（含人文标记识别），并剥掉管线注释
        book_tags = {
            "age": t["tags"]["age"],
            "language": t["tags"]["language"],
            "theme": migrate_book_themes(t["tags"], t.get("reason_zh") or ""),
        }
        reason_zh = clean_reason(t.get("reason_zh") or "")
        src0 = (b.get("sources") or [{}])[0]
        isbn = b.get("isbn") or ""
        bid = book_id(b["title"])
        local_cover = (ROOT / f"public/covers/{bid}.jpg")
        cover = f"covers/{bid}.jpg" if local_cover.exists() else (b.get("cover") or "")
        books.append({
            "id": bid,
            "source": "youtube" if is_yt else "bilibili",
            "bvid": None if is_yt else b.get("bvid"),
            "vid": b["vid"] if is_yt else None,
            "title": b["title"],
            "title_en": b.get("title_en") or TITLE_EN_OVERRIDES.get(b["title"], ""),
            "author": b.get("author") or "",
            "rating": b.get("rating"),
            "cover": cover,
            "isbn": isbn,
            "publisher": b.get("publisher") or "",
            "tags": book_tags,
            "reason": reason_zh or b.get("blurb", ""),
            "reason_en": t.get("reason_en") or "",
            "source_name": src0.get("name", ""),
            "source_url": src0.get("url", ""),
            "award": ({"id": b["award_id"], "name": b.get("award_name") or "", "year": b.get("award_year")}
                      if b.get("award_id") else None),
            "douban_url": b.get("douban_url") or "",
            "goodreads_url": goodreads_url(b),
        })
    books.sort(key=lambda x: -(x.get("rating") or 0))
    out = ROOT / "src/data/books.json"
    out.write_text(
        json.dumps({"schema_version": 1, "count": len(books), "books": books},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"打标 {len(tagged)}，收录 {len(books)}，无打标跳过 {skipped} → {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--covers", action="store_true")
    ap.add_argument("--merge", action="store_true")
    args = ap.parse_args()
    if args.collect:
        collect()
    elif args.covers:
        covers()
    elif args.merge:
        merge()
    else:
        raise SystemExit("用法: build_books.py --collect | --merge")


if __name__ == "__main__":
    main()
