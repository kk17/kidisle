# TinyCove (tinycove)

[中文](./README.md) | English

> A safe little island in the ocean of online video — for kids.

TinyCove is a **curated kids-content directory for parents**: hand-reviewed, tagged
children's videos from Bilibili and YouTube, plus high-rated children's picture books
from Douban and Goodreads communities. Filter by **age / language / topic / platform**;
videos play through the platforms' official embeds, and every picture book links to
Douban and Goodreads.

**Live site**: https://tinycove.github.io/

An independent open-source project (MIT), not affiliated with any video platform or publisher.

## Features

**🎬 Video list**
- 796 videos (519 Bilibili + 277 YouTube) filterable by age band (0-3 / 3-6 / 6-9 / 9-12), language (Chinese / English / Bilingual) and topic (10 categories)
- Watch page: big official embed (danmaku off by default), multi-part episode picker, related videos
- Platform filter (Bilibili / YouTube) with badges on every card

**📚 Picture books**
- 207 highly-rated picture books (Douban Top 100 in full + Feng Zikai Award + Caldecott Medal & Honor + Goodreads Listopia)
- Each book shows: recommendation reason (bilingual), source (linked back to the original post), title, author, rating, cover and ISBN
- Douban + Goodreads links

**Common**
- 🔁 Top-bar dropdown to switch between Videos / Picture books
- 🌐 Bilingual UI (Chinese / English) with remembered preference
- 👨‍👩‍👧 Creator directory: 467 creators with recommendation reasons and sources
- 🔗 One-click copy link / save to KikiReel
- 🗣️ One-click issue reporting from every detail page (broken video, unsuitable content, wrong metadata…)
- 🚫 No ads, no tracking, no user data collection

## Getting started

```bash
npm install
npm run dev      # dev server (http://localhost:4321/)
npm run build    # build static site to dist/
npm run preview  # preview the build
```

## Site structure

```
/                       Home: data-type dropdown (videos / books) + filters + grid
/bloggers/              Creator directory: platform / topic filters
/blogger/{up}/          Creator page: avatar, reasons, sources, all videos
/video/{bvid|vid}/      Watch page: big player + episodes + related + report button
/book/{id}/             Book detail: cover, recommendation, publication info, links, report button
```

## Data pipeline (static snapshot mode)

Site data lives in two **static snapshots** (`src/data/videos.json`, `src/data/books.json`).
The collection & tagging pipelines run offline; a new snapshot ships with a regular commit.
The site itself requests no third-party API at runtime.

```
Discovery               Collection                Review                Publish
────────────            ────────────              ────────────          ────────────
round-up articles /  →  collect.py (Bilibili)  →  review agents      →  build_data.py
Zhihu / WeChat          collect_yt.py (YT)        (shared guidelines,   build_books.py
curated lists           build_books.py --collect  sharded in parallel)  → push auto-deploys
```

| Script | Purpose |
|---|---|
| `scripts/collect.py` | Bilibili: extract BV ids from curated lists, enrich metadata (falls back to `--via html` page parsing when APIs are risk-controlled) |
| `scripts/collect_yt.py` | YouTube: extract vids, enrich via oEmbed |
| `scripts/build_books.py` | Books: parse lists, enrich via Douban suggest/detail, self-host covers (`--collect/--covers/--merge`) |
| `scripts/tagging-guidelines.md` | The single tagging standard: suitability rules + tag taxonomy |
| `scripts/merge_tags.py` | Merge video tagging batches with schema validation |
| `scripts/build_data.py` | Tagged videos → `videos.json` / `bloggers.json` (with per-channel quota) |
| `scripts/backfill_*.py` | Backfill creator avatars / episode lists |
| `scripts/tag.py` | LLM-API tagging for future incremental updates |

See [docs/data-sources.md](docs/data-sources.md) for source lists and reachability notes.

## KikiReel integration

Every watch page has a "⭐ Save to KikiReel" button configured in `src/data/site-config.json`:

```
https://play.kk17.net/family/video-search/?keyword={url}&source={source}#/search
```

`{url}` is the encodeURIComponent-ed original video link; `{source}` is `bilibili` / `youtube`. Leave empty to hide the button.

## Feedback

Something wrong with a video or book (broken, unsuitable, bad metadata, missing cover…)?
Hit **"🗣️ Report an issue"** on its detail page — it opens a pre-filled GitHub issue form.
Or pick a template directly from [Issues](https://github.com/tinycove/tinycove.github.io/issues/new/choose).

## Contributing

PRs welcome! Please read `scripts/tagging-guidelines.md` before touching data snapshots,
and add content through the pipeline rather than editing snapshots by hand.
Run `npm run build` to verify UI changes.

### Agent workflow

This project uses a dev / review / QA three-role workflow: UI changes go through an
independent review agent against a checklist, and deployments are verified by a QA agent
running a state matrix in a real browser. See [docs/agent-workflow.md](docs/agent-workflow.md).

## License

[MIT](./LICENSE) · Video and book metadata belong to their original owners; this site only indexes links and embeds official players.
