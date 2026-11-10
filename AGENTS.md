# AGENTS.md — 童心岛 (kidisle)

> 面向 agent 的项目指南。人看的文档在 [README.md](README.md) 与 [docs/](docs/)。
> 中文版为本源；英文说明见各文件内注释。

## 项目速览

儿童内容精选站：**796 条视频**（B站 519 + YouTube 277）+ **451 本绘本**，
双语（中/EN）、PWA 可安装、静态快照模式（无运行时 API 依赖）。

- 线上：https://kk17.github.io/kidisle/
- 技术栈：Astro 7 + 原生 TS，无框架依赖

## 常用命令

```bash
npm run dev          # 开发服务器（源码热更新，http://localhost:4321/kidisle）
npm run build        # 构建静态站到 dist/
npm run preview      # 预览构建产物
npm run qa           # QA 状态矩阵（对线上 https://kk17.github.io/kidisle/）
npm run qa:local     # QA 状态矩阵（对本地 dist/，自动 build）
```

## 多 Agent 协作工作流（重要）

本项目采用 **dev / review / QA 三角色协作**，详见 [docs/agent-workflow.md](docs/agent-workflow.md)：

| 角色 | 职责 | 触发 |
|---|---|---|
| Dev | 功能实现、修复 | 常规 |
| Review | 按清单审查 diff（7 项） | 每次 UI/管线改动 push 前 |
| QA | 状态矩阵断言（桌面/手机 × 视频/图书 × 双语） | 每次部署后 |

- Review/QA 由**独立 sub agent** 执行（定义在 `.zcode/agents/`），避免自查盲区
- Review 结果写入 `docs/review-YYYY-MM-DD.md`，QA 结果写入 `docs/qa-report-*.md`
- 审查清单与状态矩阵随 bug 库更新：每修一个新类型 bug，把检查方法加进对应清单
- QA 浏览器操作已脚本化（`scripts/qa-check.mjs`，零 LLM token），agent 只负责读报告与修复失败项

## 关键约定（踩过的坑，改动前必读）

- **Astro 模板补丁**：对 .astro 文件做字符串替换极易把属性挤到标签外（历史上 3 次），改完必须 `npm run build` + 浏览器验证
- **`[hidden]` 属性**：全局 `[hidden]{display:none!important}` 已兜底，新增 CSS 不得破坏该语义
- **i18n**：`data-i18n` key 必须在 `src/lib/i18n.ts` 字典中；双语内容用 `data-zh`/`data-en` 属性
- **BASE_URL**：拼接路径统一走 `src/lib/base.ts`（禁止直接用 `import.meta.env.BASE_URL`）
- **视频主题 ≠ 图书主题**：视频用 `taxonomy.themes`，绘本用 `taxonomy.book_themes`（两套独立枚举）
- **封面**：豆瓣图床拒绝热链（418），一律用 `public/covers/` 自托管（build_books.py --covers 生成）
- **数据快照**：`videos.json`/`books.json` 由管线生成，禁止手工编辑
- **sub agent 定义**：`.zcode/agents/` 下的 reviewer / qa；修改清单后同步更新

## 数据管线

打标口径：[scripts/tagging-guidelines.md](scripts/tagging-guidelines.md)。
绘本管线：[scripts/build_books.py](scripts/build_books.py)（--collect 富化 / --covers 封面自托管 / --merge 发布）。
数据来源与可达性：[docs/data-sources.md](docs/data-sources.md)。

## Astro 开发备注

开发服务器用后台模式：

```
astro dev --background
```

管理：`astro dev stop` / `astro dev status` / `astro dev logs`。

完整文档：https://docs.astro.build
