# 童心岛 (kidisle)

> 视频的汪洋里，为孩子圈出一座安全的小岛。

童心岛是一个面向家长的**中文儿童视频精选站**：收录经过筛选、打标的 B 站优质视频，
支持按**年龄段 / 语言 / 主题**三个维度快速筛选，视频直接用 B 站官方 embed 播放。
家长看到好片后可一键复制链接，粘贴进 KikiReel web 搜索框收藏。

本项目为独立开源项目（MIT），不隶属于任何视频平台。

## 特性

- 🗂 三维筛选：年龄段（0-3 / 3-6 / 6-9 / 9-12）· 语言（中文 / 英文 / 双语）· 主题
- ▶️ B 站官方 iframe embed，手机浏览器可播
- 🔗 每个视频一键复制链接，方便收藏到自己的片单工具
- 📦 纯静态站点，无后端、无追踪；数据以 JSON 快照形式随仓库发布

## 快速开始

```bash
npm install
npm run dev      # 本地开发 (http://localhost:4321)
npm run build    # 构建纯静态站点到 dist/
npm run preview  # 预览构建产物
```

## 目录结构

```
src/
  data/
    taxonomy.json    # 标签体系（年龄段 / 语言 / 主题 的枚举定义）
    videos.json      # 视频条目快照（站点唯一数据源）
  pages/
    index.astro      # 单页站入口
scripts/             # （stage 2 起）数据源采集与 LLM 打标管线
```

## 数据快照模式

站点数据来自 `src/data/videos.json` 的一份**静态快照**：采集脚本与 LLM 打标管线
定期离线运行，产出新快照后随一次 commit 发布，站点本身不请求任何第三方 API。
每个条目：

```json
{
  "id": "bv-1x2y3z",
  "source": "bilibili",
  "bvid": "BV1xx411c7mD",
  "title": "视频标题",
  "up": "UP 主名称",
  "duration_seconds": 315,
  "tags": { "age": ["3-6"], "language": ["zh"], "theme": ["science"] },
  "added_at": "2026-11-06"
}
```

> ⚠️ 当前 `videos.json` 中为 **schema 演示用的占位数据**，采集管线（stage 2）接入后
> 将被真实条目替换。

## 贡献

欢迎 PR！当前 MVP 阶段主要需求见仓库 issue 区。修改 `videos.json` 前请先阅读
`taxonomy.json` 中定义的标签枚举，保持打标一致性。

## License

[MIT](./LICENSE)
