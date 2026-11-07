# Agent 协作工作流（dev / review / QA）

本项目的功能开发采用**三角色多 agent 协作**。每个角色有明确的职责边界和触发时机。

## 角色

| 角色 | 职责 | 执行者 |
|---|---|---|
| **Dev** | 功能实现、bug 修复、数据管线 | 主 agent（或人工）|
| **Review** | 代码审查：在 push 前审计 diff，按下方「审查清单」逐项检查 | 独立 sub agent（不参与该次开发，避免自查盲区）|
| **QA** | 部署后按「状态矩阵」在真实浏览器跑断言，并截图留证 | 独立 sub agent（有浏览器访问权限）|

## 触发时机

| 变更类型 | Review | QA |
|---|---|---|
| UI 改动（模板/样式/交互）| ✅ 必须 | ✅ 必须（全矩阵）|
| 数据管线（collect/build/tag）| ✅ 必须 | ✅ 抽样验证产物 |
| 纯数据快照更新（videos/books.json）| ⭕ 抽查 | ✅ 构建通过 + 抽样页渲染 |
| 文档 | ⭕ 拼写/链接 | ❌ |

## Review 审查清单（本项目踩过的坑，逐项核对）

- [ ] Astro 模板：字符串替换补丁是否把属性挤到标签外（检查所有 `<Base>`/组件标签闭合）
- [ ] `[hidden]` 属性是否有同名 CSS `display` 规则覆盖（全局 `[hidden]{display:none!important}` 已兜底，新增 CSS 不得破坏）
- [ ] i18n：`data-i18n` 引用的 key 是否都在 `i18n.ts` 字典里；`data-tag-dim` 是否在 Base 的 tag 字典维度里
- [ ] 悬空引用：`getElementById` / `querySelector` 的目标是否存在于对应页面
- [ ] BASE_URL：拼接路径是否用 `lib/base.ts`（禁止直接用 `import.meta.env.BASE_URL`）
- [ ] 生成代码的转义：预缓存清单/JSON 注入是否对单引号、中文、方括号做了处理
- [ ] Python 脚本：`py_compile` 通过；无悬空函数引用

## QA 状态矩阵（UI 变更必跑）

维度：`模式(video/book) × 语言(zh/en) × 关键页面(index/video/book/blogger/award)`

每个组合断言：
- [ ] 顶栏元素正确（下拉值、tab/chips 显隐、EN 位置、无裸文本泄漏）
- [ ] 筛选行显隐符合当前模式（图书奖项视图仅 奖项语言 行）
- [ ] 内容区正确（视频网格/书目网格/奖项卡片墙）
- [ ] 标签已翻译（无残留中文于英文态的 UI 元素）
- [ ] 卡片/详情页核心元素存在（评分、标签、链接按钮）

部署后另跑：SW 注册（PWA）、manifest 可达、无 404 资源。

## 执行方式

- Review/QA 由主 agent 派发独立 sub agent 完成，**结果以评论形式记入对应 Multica issue**
- Review 发现的问题直接修复后复审；QA 失败阻断发布
- 清单随 bug 库更新：每修一个新类型 bug，把它的「检查方法」加进对应清单
- QA 状态矩阵细则见 [docs/qa-matrix.md](qa-matrix.md)
