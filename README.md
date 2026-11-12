# 童心湾 (tinycove)

> 在内容的汪洋里，为孩子圈出一方安静的小海湾。

[English](./README.en.md) | 中文

童心湾是一个面向家长的**儿童内容精选站**：收录经过审核、打标的 B 站与 YouTube 优质儿童视频，
以及豆瓣、Goodreads 等社区高分儿童绘本，支持按**年龄段 / 语言 / 主题 / 平台**筛选，
视频通过各平台官方播放器播放，每本绘本提供豆瓣与 Goodreads 链接。

**线上地址**：https://tinycove.github.io/

本项目为独立开源项目（MIT），不隶属于任何视频平台或出版社。

## 功能

**🎬 视频片单**
- 796 条视频（B 站 519 + YouTube 277），按年龄段（0-3 / 3-6 / 6-9 / 9-12）、语言（中文 / 英文 / 双语）、主题（科普 / 动画 / 绘本故事 / 音乐等 10 类）筛选
- 观看页：大屏官方播放器（弹幕默认关闭）、多 P 合集选集切换、相关推荐
- B 站 / YouTube 平台筛选，卡片带平台角标

**📚 绘本书单**
- 207 本高分绘本（豆瓣热门儿童绘本 Top 100 全量 + 丰子恺图画书奖 + Caldecott 奖 + Goodreads Listopia 等）
- 每本含：推荐理由（双语）、来源（可回溯原帖）、书名、作者、评分、封面、ISBN
- 豆瓣与 Goodreads 双链接

**通用**
- 🔁 顶部下拉切换 视频片单 / 绘本书单
- 🌐 站点 UI 中英双语：URL 带语言前缀（`/zh/…`、`/en/…`，分享链接固化语言）；无前缀地址按浏览器语言自动选择（中文→中文，其余→英文），手动切换会记住
- 👨‍👩‍👧 博主目录：467 位创作者，附推荐理由与来源出处
- 🔗 一键复制链接 / 收藏到 KikiReel
- 🗣️ 详情页一键反馈（视频失效、内容不适宜、信息有误等，直达 GitHub issue）
- 🚫 无广告、无追踪、无用户数据收集

## 快速开始

```bash
npm install
npm run dev      # 本地开发 (http://localhost:4321/)
npm run build    # 构建纯静态站点到 dist/
npm run preview  # 预览构建产物
```

## 站点结构

每个视图一张真实静态页（URL 统一为路径，SEO 友好），且都带语言前缀 `{lang}` = `zh` / `en`
（界面语言由 URL 决定，分享出去不变）。不带前缀的地址（如 `/video/BV1xx/`、`/`）是极小的跳转页：
按「手动选过的语言 > 浏览器首选语言（zh-* → zh，其余 → en）」跳到对应前缀，保留 query/hash，旧链接继续可用。

```
/                             按浏览器语言跳到 /zh/videos/ 或 /en/videos/（noindex）
/{lang}/                      重定向到 /{lang}/videos/
/{lang}/videos/               视频片单：平台 / 年龄 / 语言 / 主题筛选 + 视频网格
/{lang}/bloggers/             博主目录：平台 / 主题筛选 + 博主卡片墙
/{lang}/books/                绘本书单：年龄 / 语言 / 主题筛选 + 绘本网格
/{lang}/awards/               奖项目录：奖项语言筛选 + 奖项卡片墙
/{lang}/blogger/{up}/         博主页：头像 / 推荐理由 / 来源出处 / 全部视频
/{lang}/video/{bvid|vid}/     观看页：大播放器 + 选集 + UP主卡 + 相关推荐 + 反馈入口
/{lang}/book/{id}/            绘本详情页：封面 + 推荐理由 + 出版信息 + 外链 + 反馈入口
/{lang}/award/{id}/           奖项详情页：奖项介绍 + 历届获奖绘本（按年份折叠）
```

## 数据管线（静态快照模式）

站点数据是 `src/data/videos.json` 与 `src/data/books.json` 两份**静态快照**：
采集与打标管线离线运行，产出新快照后随一次 commit 发布，站点本身不请求任何第三方 API。

```
发现层                  采集层                 审核层               发布层
────────────           ────────────           ────────────         ────────────
盘点文章 / 知乎 /   →  collect.py (B站)    →  审核打标 agent     →  build_data.py
微信公众号 / 搜索引擎    collect_yt.py (YT)     (tagging-guidelines)   build_books.py
精选清单(BV/vid/书名)    build_books.py --collect  (分片并行)          → push 自动部署
```

| 脚本 | 作用 |
|---|---|
| `scripts/collect.py` | B 站：精选清单提取 BV 号，补全元数据（API 被风控时 `--via html` 走视频页解析） |
| `scripts/collect_yt.py` | YouTube：精选清单提取 vid，oEmbed 富化 |
| `scripts/build_books.py` | 绘本：清单解析 + 豆瓣 suggest/详情富化 + 封面自托管（`--collect/--covers/--merge`） |
| `scripts/tagging-guidelines.md` | 打标唯一口径：适宜性判据 + 三维标签枚举与边界规则 |
| `scripts/merge_tags.py` | 合并视频打标批次并做 schema 校验 |
| `scripts/build_data.py` | 视频打标结果 → `videos.json` / `bloggers.json`（含单频道配额） |
| `scripts/backfill_faces.py` / `backfill_pages.py` / `backfill_yt_faces.py` | 补抓博主头像 / 合集分 P / YT 频道头像 |
| `scripts/tag.py` | LLM API 批量打标（OpenAI 兼容接口，供定时增量更新） |

数据来源与可达性结论详见 [docs/data-sources.md](docs/data-sources.md)。

## KikiReel 导流

观看页提供「⭐ 收藏到 KikiReel」按钮，落地链接模板配置于 `src/data/site-config.json`：

```
https://play.kk17.net/family/video-search/?keyword={url}&source={source}#/search
```

`{url}` 为 encodeURIComponent 后的视频原链，`{source}` 为 `bilibili` / `youtube`。模板留空则隐藏按钮。

## 反馈

视频或绘本有问题（失效、不适宜、信息有误、无封面……）？
在对应**详情页点「🗣️ 反馈问题」**，会带好内容信息跳转到预填好的 GitHub issue 表单；
也可以直接在 [Issues](https://github.com/tinycove/tinycove.github.io/issues/new/choose) 里选择模板提交。

## 贡献

欢迎 PR！修改数据快照前请先阅读 `scripts/tagging-guidelines.md` 的标签口径；
新增内容请走数据管线而非手工编辑。站点 UI 改动请跑 `npm run build` 确认通过。

### Agent 协作工作流

本项目采用 dev / review / QA 三角色协作：UI 改动需经独立 review agent 按清单审查，
部署后由 QA agent 按状态矩阵在真实浏览器验证。详见 [docs/agent-workflow.md](docs/agent-workflow.md)。

## License

[MIT](./LICENSE) · 视频与图书信息版权归原权利人所有，站点仅做链接索引与官方播放器嵌入
