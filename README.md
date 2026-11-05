# 童心岛 (kidisle)

> 视频的汪洋里，为孩子圈出一座安全的小岛。

童心岛是一个面向家长的**中文儿童视频精选站**：收录经过审核、打标的 B 站优质视频（YouTube 英文区在路线图中），支持按**年龄段 / 语言 / 主题**三个维度筛选，视频通过 B 站官方播放器播放。
家长看到好片后可一键复制链接，或直接收藏进 KikiReel。

**线上地址**：https://kk17.github.io/kidisle/

本项目为独立开源项目（MIT），不隶属于任何视频平台。

## 功能

- 🗂 **三维筛选**：年龄段（0-3 / 3-6 / 6-9 / 9-12）· 语言（中文 / 英文 / 双语）· 主题（科普 / 动画 / 绘本故事 / 音乐 / 数学思维 / 英语启蒙 / 自然 / 生活习惯 / 情感与社交 / 手工）
- 🎬 **观看页**：大屏播放器（弹幕默认关闭）、多 P 合集选集切换、同博主/同主题相关推荐
- 👨‍👩‍👧 **博主目录**：145+ 位优质 UP 主，附推荐理由、内容主题与来源出处（可回溯原帖）
- 🔗 **收藏导流**：每个视频一键复制链接，或直接收藏到 KikiReel
- 🧒 弹幕默认关闭、无广告、无追踪，适合孩子观看

## 快速开始

```bash
npm install
npm run dev      # 本地开发 (http://localhost:4321/kidisle)
npm run build    # 构建纯静态站点到 dist/
npm run preview  # 预览构建产物
```

## 站点结构

```
/                       首页：三维筛选 + 视频卡片网格
/bloggers/              博主目录：主题筛选 + 博主卡片墙
/blogger/{up}/          博主页：头像 / 推荐理由 / 来源出处 / 全部视频
/video/{bvid}/          观看页：大播放器 + 选集 + UP主卡 + 相关推荐
```

## 数据管线（静态快照模式）

站点数据是 `src/data/videos.json` 的一份**静态快照**：采集与打标管线离线运行，产出新快照后随一次 commit 发布，站点本身不请求任何第三方 API。

```
发现层                 采集层                审核层              发布层
────────────          ────────────          ────────────        ────────────
盘点文章/亲子社区  →  scripts/collect.py  →  LLM/审核 agent   →  scripts/build_data.py
精选清单(BV号文本)     (视频页元数据补全)     (tagging-guidelines)  (生成 videos.json /
B站搜索线索            匿名API + HTML降级     + merge_tags.py       bloggers.json)
知乎/搜索引擎线索                                                  → push 自动部署
```

| 脚本 | 作用 |
|---|---|
| `scripts/collect.py` | 从精选清单提取 BV 号，补全标题/简介/封面/UP主/分P 列表（API 被风控时 `--via html` 走视频页解析） |
| `scripts/tagging-guidelines.md` | 打标唯一口径：适宜性判据 + 三维标签枚举与边界规则 |
| `scripts/merge_tags.py` | 合并各打标批次并做 schema 校验 |
| `scripts/build_data.py` | 打标结果 + 候选元数据 → `src/data/videos.json`、`src/data/bloggers.json` |
| `scripts/backfill_faces.py` / `backfill_pages.py` | 补抓博主头像 / 合集分 P 列表 |
| `scripts/tag.py` | LLM API 批量打标（OpenAI 兼容接口，供脱离 agent 环境的定时增量更新） |

数据来源与采集策略详见 [docs/data-sources.md](docs/data-sources.md)（B 站匿名发现接口受风控限制，发现层依赖人工精选清单与搜索引擎；已知来源均记录原文出处）。

### 数据条目示例

```json
{
  "id": "bv-1ah411o7gn",
  "source": "bilibili",
  "bvid": "BV1ah411o7GN",
  "title": "【48集全】英语幼儿启蒙 动画 Big Muzzy",
  "up": "Mmxgxg",
  "cover": "https://i0.hdslb.com/bfs/archive/....jpg",
  "total_pages": 48,
  "pages": [{ "page": 1, "part": "【001】Hello", "duration": 848 }],
  "tags": { "age": ["3-6"], "language": ["en"], "theme": ["english", "animation"] },
  "added_at": "2026-11-06"
}
```

## KikiReel 导流

观看页提供「⭐ 收藏到 KikiReel」按钮，落地链接模板配置于 `src/data/site-config.json`：

```
https://play.kk17.net/family/video-search/?keyword={url}&source={source}#/search
```

`{url}` 为 encodeURIComponent 后的视频原链，`{source}` 为 `bilibili` / `youtube`。模板留空则隐藏按钮。

## 路线图

- [x] B 站中文区 MVP（三维筛选 / 观看页 / 博主目录 / 合集选集 / KikiReel 导流）
- [ ] 知乎推荐来源纳入发现层（RIGE-772）
- [ ] YouTube 英文区收录 + 站点中英文 UI 切换（RIGE-779）
- [ ] 合规自查与正式发布（RIGE-780）

## 贡献

欢迎 PR！修改 `videos.json` 前请先阅读 `scripts/tagging-guidelines.md` 的标签口径；
新增视频请走数据管线而非手工编辑。站点 UI 改动请跑 `npm run build` 确认通过。

## License

[MIT](./LICENSE) · 视频内容版权归原 UP 主所有，站点仅做链接索引与官方播放器嵌入
