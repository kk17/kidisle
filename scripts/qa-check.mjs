#!/usr/bin/env node
/**
 * 童心湾 QA 状态矩阵自动化检查（零 LLM token）
 *
 * 维度：页面(videos/books/awards/bloggers/详情页) × 语言(zh/en) × 视口(desktop/mobile)
 * URL 方案（RIGE-1021 + RIGE-1080）：每个视图一张真实静态页，带语言前缀 /zh/... /en/...；无前缀地址按浏览器语言跳转
 * 用法：
 *   node scripts/qa-check.mjs                # 测线上 https://tinycove.github.io
 *   node scripts/qa-check.mjs --local        # 测 dist/（需先 npm run build，脚本自带静态服务器）
 *   BASE=http://host node scripts/qa-check.mjs   # 测任意已部署地址
 * 退出码：全部通过 0，任一失败 1
 */
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';

const LOCAL = process.argv.includes('--local');
let target = (process.env.BASE || 'https://tinycove.github.io').replace(/\/$/, '');
const results = [];
let browser;
let localServer;

// --local：把 dist/ 服务在根路径（与 GitHub Pages 组织站一致）
function startLocalServer(prefix = '') {
	const root = fileURLToPath(new URL('../dist/', import.meta.url));
	return new Promise((resolve) => {
		const srv = http.createServer((req, res) => {
			const u = new URL(req.url, 'http://x');
			let p = decodeURIComponent(u.pathname);
			if (p.startsWith(prefix)) p = p.slice(prefix.length) || '/';
			let file = root + p.split('?')[0];
			if (file.endsWith('/')) file += 'index.html';
			const mime = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
				'.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml',
				'.png': 'image/png', '.jpg': 'image/jpeg', '.webp': 'image/webp',
				'.woff2': 'font/woff2', '.ico': 'image/x-icon' }[file.slice(file.lastIndexOf('.'))] || 'application/octet-stream';
			try {
				const c = readFileSync(file);
				res.writeHead(200, { 'Content-Type': mime });
				res.end(c);
			} catch {
				res.writeHead(404);
				res.end('not found');
			}
		});
		srv.listen(0, () => {
			localServer = srv; // 捕获服务器对象，跑完关闭让进程正常退出
			resolve(`http://localhost:${srv.address().port}`);
		});
	});
}

function record(id, ok, detail = '') {
	results.push({ id, ok, detail });
	console.log(`${ok ? '✅' : '❌'} ${id}${detail ? ' — ' + detail : ''}`);
}

async function title(page) { return page.evaluate(() => document.title); }
async function pathName(page) { return new URL(page.url()).pathname; }
async function noLeak(page) {
	return page.evaluate(() => !document.body.innerText.slice(0, 300).includes('description='));
}

// ---- 根路径重定向 ----
async function testRootRedirect(page) {
	await page.goto(`${target}/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(1200);
	const p = await pathName(page);
	record('R-1 根路径 / 按浏览器语言重定向到 /zh/videos/（zh-CN 浏览器）', p === '/zh/videos/', p);
}

// ---- 视频片单 /videos/（中文桌面）----
async function testVideosZh(page) {
	await page.goto(`${target}/zh/videos/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(800);
	const s = await page.evaluate(() => {
		const vis = (id) => { const el = document.getElementById(id); return el && getComputedStyle(el).display !== 'none'; };
		return {
			sel: document.getElementById('datatype').value,
			navtabs: vis('navtabs'), chipsHidden: !vis('bookview-chips'),
			cur: document.querySelector('#navtabs a[aria-current="page"] span')?.textContent,
			logomark: Boolean(document.querySelector('.logo img.logomark')),
			rows: document.querySelectorAll('#video-filters .filter-row').length,
			cards: document.querySelectorAll('#grid .cell:not([style*="none"])').length,
			badges: document.querySelectorAll('#grid .vtitle .vsrc').length,
			count: document.getElementById('count').textContent,
		};
	});
	record('D-V-1 下拉=video / tab 可见 / chips 隐藏', s.sel === 'video' && s.navtabs && s.chipsHidden, `sel=${s.sel}`);
	record('D-V-2 视频 tab aria-current + 顶栏 logo 图标', s.cur === '视频' && s.logomark, s.cur);
	record('D-V-3 四行筛选可见', s.rows === 4, `实际 ${s.rows}`);
	record('D-V-4 卡片数 = 796 且标题来源图标齐全', s.cards === 796 && s.badges >= 796, `cards=${s.cards} badges=${s.badges}`);
	record('D-V-5 计数样式 shown / total', s.count === '796 / 796', s.count);
	const yt = await page.evaluate(() => {
		const chip = [...document.querySelectorAll('#video-filters .chip')].find(c => c.dataset.v === 'youtube');
		chip.click();
		return document.getElementById('count').textContent;
	});
	record('D-V-6 YouTube 筛选联动', parseInt(yt) > 0 && yt !== '796 / 796', yt);
	// 平台「全部」复位（RIGE-1021 review：plat-all 此前是死按钮，补回归断言）
	const reset = await page.evaluate(() => {
		const chip = [...document.querySelectorAll('#video-filters .chip')].find(c => c.dataset.v === 'bilibili');
		chip.click();
		document.getElementById('plat-all').click();
		return {
			count: document.getElementById('count').textContent,
			pressed: document.getElementById('plat-all').getAttribute('aria-pressed'),
		};
	});
	record('D-V-7 平台「全部」复位联动', reset.count === '796 / 796' && reset.pressed === 'true', `${reset.count} pressed=${reset.pressed}`);
	const t1 = await title(page);
	record('D-V-8 标题双语（zh 默认）', t1.includes('童心湾'), t1);
	record('D-V-9 无裸文本泄漏', await noLeak(page));
}

// ---- 绘本书单 /books/（中文桌面）----
async function testBooksZh(page) {
	await page.goto(`${target}/zh/books/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(800);
	const s = await page.evaluate(() => {
		const vis = (id) => { const el = document.getElementById(id); return el && getComputedStyle(el).display !== 'none'; };
		const dims = [...document.querySelectorAll('#book-filters .dim')].map(d => d.textContent.trim());
		return {
			sel: document.getElementById('datatype').value,
			navtabsHidden: !vis('navtabs'), chips: vis('bookview-chips'),
			booksChipCur: document.getElementById('bv-books')?.getAttribute('aria-current'),
			dims,
			bookCards: document.querySelectorAll('#book-grid .bookcell:not([style*="none"])').length,
			count: document.getElementById('book-count').textContent,
			themeChips: [...document.querySelectorAll('#book-filters .chip[data-dim="theme"]')].map(c => c.textContent.trim()),
		};
	});
	record('D-B-1 下拉=book / tab 隐藏 / chips 显示', s.sel === 'book' && s.navtabsHidden && s.chips, `sel=${s.sel}`);
	record('D-B-2 书目 chip aria-current', s.booksChipCur === 'page', String(s.booksChipCur));
	record('D-B-3 筛选行 = 年龄/语言/主题（无奖项语言）', s.dims.length === 3 && !s.dims.includes('奖项语言'), s.dims.join(','));
	record('D-B-4 绘本 451 本', s.bookCards === 451, `实际 ${s.bookCards}`);
	record('D-B-5 计数样式 shown / total', s.count === '451 / 451', s.count);
	record('D-B-6 图书专属主题 9 类（interactive 已移除）', s.themeChips.length === 9 && !s.themeChips.includes('动画'), s.themeChips.join('/'));
	// 顶栏 奖项 chip → 导航到 /awards/
	await page.click('#bv-awards');
	await page.waitForLoadState('domcontentloaded');
	const p = await pathName(page);
	record('D-B-7 顶栏「奖项」chip 跳转 /zh/awards/', p === '/zh/awards/', p);
}

// ---- 奖项目录 /awards/（中文桌面）----
async function testAwardsZh(page) {
	await page.goto(`${target}/zh/awards/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(800);
	const s = await page.evaluate(() => {
		const vis = (id) => { const el = document.getElementById(id); return el && getComputedStyle(el).display !== 'none'; };
		return {
			sel: document.getElementById('datatype').value,
			navtabsHidden: !vis('navtabs'), chips: vis('bookview-chips'),
			awardsChipCur: document.getElementById('bv-awards')?.getAttribute('aria-current'),
			dim: document.querySelector('#award-filters .dim')?.textContent.trim(),
			awardCards: document.querySelectorAll('#award-grid .awardcell:not([style*="none"])').length,
			count: document.getElementById('award-count').textContent,
		};
	});
	record('D-A-1 下拉=book / tab 隐藏 / chips 显示', s.sel === 'book' && s.navtabsHidden && s.chips, `sel=${s.sel}`);
	record('D-A-2 奖项 chip aria-current', s.awardsChipCur === 'page', String(s.awardsChipCur));
	record('D-A-3 仅奖项语言一行筛选', s.dim === '奖项语言', s.dim);
	record('D-A-4 奖项 10 张卡片', s.awardCards === 10, `实际 ${s.awardCards}`);
	record('D-A-5 计数样式 shown / total', s.count === '10 / 10', s.count);
	// 中文态：奖项名中英同显（主标题中文 + 副标题英文）
	const zhName = await page.evaluate(() => {
		const card = document.querySelector('#award-grid .awardcell');
		return {
			name: card.querySelector('.awardname').textContent.trim(),
			en: card.querySelector('.awardname-en').textContent.trim(),
			enVisible: getComputedStyle(card.querySelector('.awardname-en')).display !== 'none',
		};
	});
	record('D-A-8 中文态奖项名中英同显', zhName.name === '凯迪克奖' && zhName.en === 'Caldecott Medal' && zhName.enVisible, `${zhName.name}/${zhName.en}`);
	// 英文奖项筛选联动
	const en = await page.evaluate(() => {
		const chip = [...document.querySelectorAll('#award-filters .chip')].find(c => c.dataset.awardLang === 'en');
		chip.click();
		return {
			shown: document.querySelectorAll('#award-grid .awardcell:not([style*="none"])').length,
			count: document.getElementById('award-count').textContent,
		};
	});
	record('D-A-6 英文奖项筛选 = 3 张', en.shown === 3 && en.count === '3 / 10', `${en.shown} ${en.count}`);
	await page.evaluate(() => document.getElementById('award-lang-all').click());
	// 顶栏 书目 chip → 导航回 /books/
	await page.click('#bv-books');
	await page.waitForLoadState('domcontentloaded');
	const p = await pathName(page);
	record('D-A-7 顶栏「书目」chip 跳转 /zh/books/', p === '/zh/books/', p);
}

// ---- 英文态（videos / books / awards）----
async function testEn(page) {
	await page.goto(`${target}/zh/videos/?v=1#qa`);
	await page.waitForLoadState('domcontentloaded');
	// RIGE-1080：切换 = 跳到另一语言前缀的同一页面，保留 query/hash
	await page.click('#lang-toggle');
	await page.waitForURL(/\/en\/videos\//);
	await page.waitForTimeout(400);
	const u0 = new URL(page.url());
	record('D-E-0 切换语言跳到 /en/ 同页并保留 query/hash', u0.pathname === '/en/videos/' && u0.search === '?v=1' && u0.hash === '#qa', u0.pathname + u0.search + u0.hash);
	const en = await page.evaluate(() => ({
		title: document.title,
		nav: document.querySelector('[data-i18n="nav_videos"]').textContent,
		brand: document.querySelector('.logo').textContent.trim(),
		leak: [...document.querySelectorAll('.site-header span, #video-filters .dim')].filter(el => /[\u4e00-\u9fa5]/.test(el.textContent)).map(e => e.textContent),
	}));
	record('D-E-1 标题英文', /TinyCove/.test(en.title), en.title);
	record('D-E-2 导航英文', en.nav === 'Videos', en.nav);
	record('D-E-3 顶栏无残留中文', en.leak.length === 0, en.leak.join(','));
	record('D-E-4 品牌名 TinyCove', en.brand.includes('TinyCove'), en.brand);

	await page.goto(`${target}/en/books/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(400);
	const bk = await page.evaluate(() => ({
		dims: [...document.querySelectorAll('#book-filters .dim')].map(d => d.textContent.trim()),
	}));
	record('D-E-5 书目页维度英文', bk.dims.join(',') === 'Age,Language,Topic', bk.dims.join(','));

	await page.goto(`${target}/en/awards/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(400);
	const aw = await page.evaluate(() => ({
		dim: document.querySelector('#award-filters .dim').textContent.trim(),
		chip: [...document.querySelectorAll('#award-filters .chip')].map(c => c.textContent.trim()),
	}));
	record('D-E-6 奖项页筛选英文', aw.dim === 'Award language' && aw.chip.join(',') === 'All,Chinese awards,English awards,International awards', `${aw.dim} ${aw.chip.join(',')}`);

	// 英文态奖项卡：只显示英文名（副标题隐藏），地区英文
	const awEn = await page.evaluate(() => {
		const card = document.querySelector('#award-grid .awardcell');
		return {
			name: card.querySelector('.awardname').textContent.trim(),
			enHidden: getComputedStyle(card.querySelector('.awardname-en')).display === 'none',
			region: card.querySelector('[data-zh][data-en]:not(.awardname):not(.awardintro)').textContent.trim(),
		};
	});
	record('D-E-7 英文态奖项仅英文名 + 地区英文', awEn.name === 'Caldecott Medal' && awEn.enHidden && awEn.region === 'USA', `${awEn.name} hidden=${awEn.enHidden} region=${awEn.region}`);

	// 页脚 i18n
	await page.goto(`${target}/en/videos/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(400);
	const footer = await page.evaluate(() => document.querySelector('.site-footer').textContent);
	record('D-E-8 页脚英文（独立开源项目已翻译）', /Independent open-source project/.test(footer) && !/独立开源项目/.test(footer), footer.trim().slice(-80));

	await page.click('#lang-toggle'); // 切回中文
	await page.waitForURL(/\/zh\/videos\//);
}

// ---- 详情页 ----
async function testVideoDetail(page) {
	await page.goto(`${target}/zh/video/BV11341157Wz/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(1000);
	const d = await page.evaluate(() => {
		const first300 = document.body.innerText.slice(0, 300);
		return {
			player: Boolean(document.querySelector('.player iframe')),
			feedback: Boolean(document.querySelector('a.feedback[href*="video-feedback.yml"]')),
			bili: Boolean(document.querySelector('a[href*="bilibili.com/video"]')),
			related: document.querySelectorAll('.related .bkcard, .related .vcard').length,
			leak: first300.includes('description='),
			title: document.title,
		};
	});
	record('V-1 播放器渲染', d.player);
	record('V-2 无裸文本泄漏', !d.leak);
	record('V-3 反馈按钮（预填模板）', d.feedback);
	record('V-4 B站原链存在', d.bili);
	record('V-5 相关推荐存在', d.related > 0, `${d.related} 条`);
	record('V-6 标题含视频名', d.title.includes('童心湾'), d.title);
}

async function testBookDetail(page) {
	await page.goto(`${target}/zh/book/bk-2c634c61c964/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(1000);
	const d = await page.evaluate(() => {
		const img = document.querySelector('.coverwrap img');
		return {
			cover: img ? img.naturalWidth > 0 : false,
			reason: (document.querySelector('.reason')?.textContent || '').length > 5,
			isbn: [...document.querySelectorAll('.facts dd')].some(x => /\d{10,}/.test(x.textContent)),
			douban: Boolean(document.querySelector('a[href*="douban.com"]')),
			gr: Boolean(document.querySelector('a[href*="goodreads.com"]')),
			src: Boolean(document.querySelector('.srcbadge, .linkrow .srcbadge')),
			feedback: Boolean(document.querySelector('a.feedback[href*="book-feedback.yml"]')),
		};
	});
	record('B-1 封面加载', d.cover);
	record('B-2 推荐理由非空', d.reason);
	record('B-3 ISBN 在出版信息', d.isbn);
	record('B-4 豆瓣链接', d.douban);
	record('B-5 Goodreads 链接', d.gr);
	record('B-6 来源徽章', d.src);
	record('B-7 反馈按钮（预填模板）', d.feedback);
}

async function testAwardDetail(page) {
	await page.goto(`${target}/zh/award/caldecott/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(1000);
	const d = await page.evaluate(() => ({
		intro: (document.querySelector('.aintro')?.textContent || '').length > 20,
		years: document.querySelectorAll('.ygroup').length,
		cards: document.querySelectorAll('.ygroup .bkcard').length,
		official: Boolean(document.querySelector('a.aofficial')),
	}));
	record('A-1 奖项介绍', d.intro);
	record('A-2 按年份折叠组', d.years > 0, `${d.years} 组`);
	record('A-3 获奖书卡片', d.cards > 0, `${d.cards} 本`);
	record('A-4 官网链接', d.official);
}

// ---- 移动端 ----
async function testMobile(page) {
	await page.setViewportSize({ width: 375, height: 812 });
	await page.goto(`${target}/zh/videos/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(600);
	const video = await page.evaluate(() => ({
		noHScroll: document.documentElement.scrollWidth <= window.innerWidth + 1,
	}));
	record('M-V-1 无横向滚动', video.noHScroll);
	const tabH = await page.evaluate(() => Math.round(document.querySelector('.navtabs a').getBoundingClientRect().height));
	record('M-V-2 tab 文字不竖排（高度正常）', tabH > 20 && tabH < 50, `${tabH}px`);
	// 下拉切图书 → 跳转 /books/
	await page.selectOption('#datatype', 'book');
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(600);
	const murl = await pathName(page);
	const book = await page.evaluate(() => ({
		chipsShown: getComputedStyle(document.getElementById('bookview-chips')).display !== 'none',
		navtabsHidden: getComputedStyle(document.getElementById('navtabs')).display === 'none',
		noHScroll: document.documentElement.scrollWidth <= window.innerWidth + 1,
	}));
	record('M-B-0 下拉切图书跳转 /zh/books/', murl === '/zh/books/', murl);
	record('M-B-1 图书模式 chips 顶栏显示', book.chipsShown);
	record('M-B-2 tab 隐藏', book.navtabsHidden);
	record('M-B-3 无横向滚动', book.noHScroll);
	// 顶栏布局（RIGE-1021 反馈轮）：语言切换贴右上角；下拉紧靠站名右侧
	await page.goto(`${target}/zh/videos/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(600);
	const head = await page.evaluate(() => {
		const r = (el) => { const b = document.querySelector(el).getBoundingClientRect(); return { left: b.left, right: b.right, top: b.top }; };
		return {
			vw: window.innerWidth,
			toggle: r('#lang-toggle'),
			logo: r('.logo'),
			modebar: r('.modebar'),
		};
	});
	record('M-H-1 语言切换贴右上角（与桌面一致）', Math.abs(head.toggle.right - head.vw) <= 24 && head.toggle.top < 60, `right距=${(head.vw - head.toggle.right).toFixed(0)}px`);
	record('M-H-2 下拉紧靠站名右侧', head.modebar.left - head.logo.right >= -6 && head.modebar.left - head.logo.right < 40, `间距=${(head.modebar.left - head.logo.right).toFixed(0)}px`);
	await page.setViewportSize({ width: 1280, height: 800 });
}

async function testMobileBloggers(page) {
	await page.setViewportSize({ width: 375, height: 812 });
	await page.goto(`${target}/zh/bloggers/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(600);
	const m = await page.evaluate(() => {
		const chips = [...document.querySelectorAll('#themebar .chip')].map(c => Math.round(c.getBoundingClientRect().height));
		return { noHScroll: document.documentElement.scrollWidth <= window.innerWidth + 1,
			maxChipH: Math.max(...chips), chipCount: chips.length,
			count: document.getElementById('count')?.textContent || '' };
	});
	record('M-C-1 博主页主题行无溢出', m.noHScroll);
	record('M-C-2 主题 chips 文字不竖排', m.chipCount >= 9 && m.maxChipH > 20 && m.maxChipH < 50, `${m.chipCount} chips max ${m.maxChipH}px`);
	record('M-C-3 博主页计数样式 shown / total', /^467 \/ 467$/.test(m.count.trim()), m.count);
	// RIGE-1021 反馈轮：博主页提示行已移除（与其他列表页风格一致）
	const hasIntro = await page.evaluate(() => document.body.innerText.includes('点进博主'));
	record('M-C-4 博主页无「点进博主」提示行', !hasIntro, '');
	await page.setViewportSize({ width: 1280, height: 800 });
}

async function testPWA(page) {
	await page.setViewportSize({ width: 1280, height: 800 });
	await page.goto(`${target}/zh/videos/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(4000);
	const pwa = await page.evaluate(async () => {
		const reg = await navigator.serviceWorker.getRegistration('/');
		const m = await (await fetch(document.querySelector('link[rel="manifest"]').href)).json();
		return { sw: Boolean(reg?.active || reg?.installing), scope: reg?.scope || null,
			manifestIcons: m.icons?.length || 0, display: m.display };
	});
	record('P-1 SW 注册/安装', pwa.sw, pwa.scope || '');
	record('P-2 manifest 3 图标 + standalone', pwa.manifestIcons >= 3 && pwa.display === 'standalone');
}

// PWA 添加到主屏幕引导（RIGE-1078）：手机首次访问按端弹出对应指引；关闭后不再自动弹；桌面不弹
async function testInstallGuide() {
	const UA = {
		ios: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1',
		android: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
		inapp: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.50(0x18003237) NetType/WIFI Language/zh_CN',
	};
	const visible = (page, sel) => page.evaluate((s) => {
		const el = document.querySelector(s);
		return Boolean(el && !el.closest('[hidden]') && el.getClientRects().length);
	}, sel);
	for (const [kind, ua] of Object.entries(UA)) {
		const ctx = await browser.newContext({ userAgent: ua, viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true, serviceWorkers: 'block' });
		const page = await ctx.newPage();
		await page.goto(`${target}/zh/videos/`);
		await page.waitForSelector('#install-guide:not([hidden])', { timeout: 6000 }).catch(() => {});
		const shown = await visible(page, '#install-guide .ig-sheet');
		const steps = await visible(page, `#install-guide [data-variant="${kind}"]`);
		const others = await page.evaluate((k) => [...document.querySelectorAll('#install-guide [data-variant]')]
			.filter((el) => !el.hidden && el.dataset.variant !== k).map((el) => el.dataset.variant), kind);
		record(`I-1 ${kind} 首访弹出对应指引`, shown && steps && others.length === 0, others.join(','));
		await page.click('#ig-ok');
		await page.reload();
		await page.waitForTimeout(3500);
		record(`I-2 ${kind} 关闭后不再自动弹`, !(await visible(page, '#install-guide .ig-sheet')));
		await page.click('#pwa-guide-open');
		record(`I-3 ${kind} 页脚入口可再次打开`, await visible(page, '#install-guide .ig-sheet'));
		await ctx.close();
	}
	const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, serviceWorkers: 'block' });
	const page = await ctx.newPage();
	await page.goto(`${target}/zh/videos/`);
	await page.waitForTimeout(3500);
	record('I-4 桌面不弹引导、无页脚入口', !(await visible(page, '#install-guide .ig-sheet')) && !(await visible(page, '#pwa-guide-open')));
	await ctx.close();
}

// ---- URL 语言前缀 + 浏览器语言自动检测（RIGE-1080）----
// 无前缀地址按「手动选过的语言 > 浏览器首选语言（中文→zh，其余→en）」跳到 /zh/ 或 /en/；带前缀的地址语言固定
async function testLangAuto() {
	const landing = async (locale, path, saved) => {
		const ctx = await browser.newContext({ locale, viewport: { width: 1280, height: 800 }, serviceWorkers: 'block' });
		if (saved) await ctx.addInitScript((v) => { try { localStorage.setItem('tinycove-lang', v); } catch {} }, saved);
		const page = await ctx.newPage();
		await page.goto(`${target}${path}`);
		await page.waitForURL(/\/(zh|en)\//, { timeout: 5000 }).catch(() => {});
		await page.waitForLoadState('domcontentloaded');
		await page.waitForTimeout(500);
		const u = new URL(page.url());
		const info = await page.evaluate(() => ({
			lang: document.documentElement.lang,
			nav: document.querySelector('[data-i18n="nav_videos"]')?.textContent,
			visible: getComputedStyle(document.body).visibility,
			links: [...document.querySelectorAll('a[href^="/"]')].map((a) => a.getAttribute('href'))
				.filter((h) => !/\.(png|svg|jpg|webmanifest)$/.test(h)),
		}));
		await ctx.close();
		return { path: u.pathname + u.search + u.hash, ...info };
	};
	const a = await landing('zh-CN', '/');
	record('L-1 中文浏览器访问 / → /zh/videos/', a.path === '/zh/videos/' && a.nav === '视频', `${a.path} nav=${a.nav}`);
	const b = await landing('en-US', '/');
	record('L-2 英文浏览器访问 / → /en/videos/（英文界面、已显示）', b.path === '/en/videos/' && b.nav === 'Videos' && b.lang === 'en' && b.visible === 'visible', `${b.path} nav=${b.nav} lang=${b.lang} vis=${b.visible}`);
	const c = await landing('ja-JP', '/video/BV11341157Wz/?x=1#t');
	record('L-3 非中文浏览器访问旧详情页地址 → /en/ 同页并保留 query/hash', c.path === '/en/video/BV11341157Wz/?x=1#t', c.path);
	const d = await landing('zh-TW', '/books/');
	record('L-4 zh-TW 也算中文 → /zh/books/', d.path === '/zh/books/', d.path);
	const e = await landing('en-US', '/videos/', 'zh');
	record('L-5 手动选过中文的偏好优先于浏览器语言', e.path === '/zh/videos/', e.path);
	const f = await landing('zh-CN', '/en/video/BV11341157Wz/');
	record('L-6 分享的 /en/ 链接在中文浏览器仍是英文', f.path === '/en/video/BV11341157Wz/' && f.nav === 'Videos', `${f.path} nav=${f.nav}`);
	const bad = f.links.filter((h) => !h.startsWith('/en/'));
	record('L-7 /en/ 页面内站内链接全部带 /en/ 前缀', bad.length === 0 && f.links.length > 5, bad.slice(0, 3).join(','));

	// PWA 引导多语言：/en/ 页面手机首访 → 英文文案
	const ctx = await browser.newContext({ locale: 'en-US', userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1', viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true, serviceWorkers: 'block' });
	const page = await ctx.newPage();
	await page.goto(`${target}/en/videos/`);
	await page.waitForSelector('#install-guide:not([hidden])', { timeout: 6000 }).catch(() => {});
	const g = await page.evaluate(() => ({
		title: document.getElementById('ig-title')?.textContent,
		ok: document.getElementById('ig-ok')?.textContent,
		cjk: [...document.querySelectorAll('#install-guide [data-variant="ios"] li, #install-guide .ig-title, #install-guide .ig-intro')]
			.filter((el) => /[\u4e00-\u9fa5]/.test(el.textContent)).length,
	}));
	record('L-8 /en/ 页面 PWA 引导为英文', g.title === 'Add TinyCove to your Home Screen' && g.ok === 'Got it' && g.cjk === 0, `${g.title} / ${g.ok} cjk=${g.cjk}`);
	await ctx.close();
}

// ---- 主流程 ----
(async () => {
	if (LOCAL) {
		target = await startLocalServer();
		console.log(`本地模式：${target}`);
	}
	browser = await chromium.launch();
	const page = await browser.newPage({ viewport: { width: 1280, height: 800 }, locale: 'zh-CN' });
	try {
		await testRootRedirect(page);
		await testVideosZh(page);
		await testBooksZh(page);
		await testAwardsZh(page);
		await testEn(page);
		await testVideoDetail(page);
		await testBookDetail(page);
		await testAwardDetail(page);
		await testMobile(page);
		await testMobileBloggers(page);
		await testPWA(page);
		await testInstallGuide();
		await testLangAuto();
	} catch (e) {
		record('FATAL', false, e.message.slice(0, 200));
	}
	await browser.close();
	if (localServer) localServer.close();

	const failed = results.filter(r => !r.ok);
	console.log('\n========== QA 报告 ==========');
	console.log(`通过 ${results.length - failed.length} / ${results.length}`);
	if (failed.length) {
		console.log('失败项：');
		failed.forEach(f => console.log(`  ❌ ${f.id} — ${f.detail}`));
		process.exit(1);
	}
	console.log('全部通过 ✅');
})();
