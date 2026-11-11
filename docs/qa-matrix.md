# QA 状态矩阵（部署后必跑）

维度：`页面(videos/books/awards/bloggers/详情页) × 语言(zh/en) × 视口(desktop/mobile)`。
由 QA agent 在真实浏览器执行，全部断言通过才算部署成功。

自动化脚本：`node scripts/qa-check.mjs`（线上）／`npm run qa:local`（构建产物），64 项断言零 LLM token。
URL 方案（RIGE-1021 起）：每个视图一张真实静态页，`/` 重定向到 `/videos/`，无 hash 模式。

## 断言清单

### 根路径
- [ ] `/` 自动重定向到 `/videos/`（meta refresh + JS 兜底）

### 顶栏（所有页面，服务端渲染 aria-current，无 JS 同步）
- [ ] logo（C 形海湾 SVG 图标，RIGE-1021 反馈轮）显示、点击回 `/videos/`
- [ ] 下拉值与当前页面一致；切换即跳转（video ↔ /videos/，book ↔ /books/）
- [ ] 视频页/博主页显示 视频/博主 tab；书目/奖项页显示 书目/奖项 chips（互斥）
- [ ] 书目/奖项 chips 为真实链接，aria-current 指向当前页
- [ ] EN/中文 切换按钮就位
- [ ] 无裸文本泄漏（检查 body 前 200 字符不含 `description=`、`titleEn` 等）
- [ ] 每页有 canonical link

### /videos/（视频片单）
- [ ] 平台/年龄段/语言/主题 四行筛选可见且可交互
- [ ] 卡片数与 videos.json 一致（796）；平台角标存在
- [ ] 计数样式 `shown / total`（与书目/博主/奖项一致），筛选联动变化
- [ ] 平台「全部」chip 复位联动（曾为死按钮的回归点）

### /books/（绘本书单）
- [ ] 年龄/语言/主题 三行筛选；**不得出现 奖项语言 行**（RIGE-1021 回归点）
- [ ] 卡片数与 books.json 一致（451）；计数 `451 / 451`
- [ ] 顶栏「奖项」chip 跳转 /awards/

### /awards/（奖项目录）
- [ ] 仅 奖项语言 一行筛选；奖项卡片墙 10 张
- [ ] 语言筛选联动（英文奖项 = 3 张）；计数 `shown / total`
- [ ] 中文态奖项名中英同显（主标题中文 + 英文副标题，D-A-8）
- [ ] 英文态奖项**仅英文名**、副标题隐藏、地区英文 region_en（D-E-7，RIGE-1021 反馈轮回归点）
- [ ] 顶栏「书目」chip 跳转 /books/
- [ ] 点击奖项卡片进入 /award/{id}/（RIGE-1021 回归点：奖项视图不再依赖 hash 切换）

### 视频详情页
- [ ] 播放器渲染、复制链接、反馈按钮、UP主卡、相关推荐
- [ ] tab 标题含视频名

### 绘本详情页
- [ ] 大封面加载、推荐理由(双语)、出版信息、豆瓣/Goodreads/来源链接、反馈按钮

### 奖项详情页
- [ ] 奖项介绍、按年份折叠组、获奖书卡片、官网链接

### 博主页 / 博主目录
- [ ] 头像加载、理由、来源徽章、视频列表
- [ ] 博主目录计数样式 `467 / 467`（与视频页一致，RIGE-1021 回归点）
- [ ] **无「点进博主」提示行**（RIGE-1021 反馈轮移除，M-C-4）

### 英文态（videos / books / awards）
- [ ] 标题/导航/品牌名英文；筛选维度英文（Age/Language/Topic、Award language）
- [ ] 各页面 UI 元素无残留中文
- [ ] 页脚「独立开源项目」英文为 Independent open-source project（D-E-8，RIGE-1021 反馈轮）

### 移动端（375px）
- [ ] videos / books / bloggers 无横向滚动；tab/chip 文字不竖排
- [ ] 语言切换按钮贴右上角、下拉紧靠站名右侧（M-H-1/2，RIGE-1021 反馈轮）

### PWA
- [ ] manifest 200、SW 注册 active、无 404 资源

## 执行记录

| 日期 | commit | 结果 | 执行者 |
|---|---|---|---|
| 2026-11-07 | 5c7dba9 | 手动注册验证 ✅（工作台浏览器） | QA |
| 2026-11-11 | cbdf1d3（迁移） | 线上 42/42 ✅ | QA |
| 2026-11-11 | 52d84cc（RIGE-1021 URL 统一） | 线上 58/58 ✅ + QA agent 人工级复核 29 项 ✅（家长 3 bug 回归点全过、0 控制台报错） | QA |
