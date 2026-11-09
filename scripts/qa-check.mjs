#!/usr/bin/env node
/**
 * 童心岛 QA 状态矩阵自动化检查（零 LLM token）
 *
 * 维度：模式(video/book) × 语言(zh/en) × 视口(desktop/mobile) × 关键页面
 * 用法：
 *   node scripts/qa-check.mjs                # 测线上 https://kk17.github.io/kidisle/
 *   node scripts/qa-check.mjs --local        # 先构建？否——需先 npm run build，脚本自带静态服务器测 dist/
 *   BASE=http://host/kidisle node scripts/qa-check.mjs   # 测任意已部署地址
 * 退出码：全部通过 0，任一失败 1
 */
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';

const LOCAL = process.argv.includes('--local');
let target = (process.env.BASE || 'https://kk17.github.io/kidisle').replace(/\/$/, '');
const results = [];
let browser;
let localServer;

// --local：把 dist/ 挂载到 /kidisle 子路径（与 GitHub Pages 结构一致）
function startLocalServer(prefix = '/kidisle') {
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
		srv.listen(0, () => resolve(`http://localhost:${srv.address().port}`));
	});
}

function record(id, ok, detail = '') {
	results.push({ id, ok, detail });
	console.log(`${ok ? '✅' : '❌'} ${id}${detail ? ' — ' + detail : ''}`);
}

async function text(page) { return page.evaluate(() => document.title); }
async function noLeak(page) {
	return page.evaluate(() => !document.body.innerText.slice(0, 300).includes('description='));
}
async function noHScroll(page) {
	return page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1);
}

async function testDesktopVideoZh(page) {
	await page.goto(`${target}/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(800);
	const sel = page.locator('#datatype');
	await sel.selectOption('video');
	const state = await page.evaluate(() => {
		const vis = (id) => getComputedStyle(document.getElementById(id)).display !== 'none';
		const rows = [...document.querySelectorAll('#video-filters .filter-row')].filter(r => getComputedStyle(r).display !== 'none').length;
		return {
			navtabs: vis('navtabs'), chipsHidden: !vis('bookview-chips'),
			videoSection: vis('video-section'), bookSectionHidden: !vis('book-section'),
			filterRows: rows,
			cards: document.querySelectorAll('#grid .cell:not([style*="none"])').length,
			badges: document.querySelectorAll('#grid .vplat').length,
			count: document.getElementById('count').textContent,
		};
	});
	record('D-V-1 顶栏：tab 可见 / chips 隐藏', state.navtabs && state.chipsHidden);
	record('D-V-2 视频区可见 / 图书区隐藏', state.videoSection && state.bookSectionHidden);
	record('D-V-3 四行筛选可见', state.filterRows === 4, `实际 ${state.filterRows}`);
	record('D-V-4 卡片数 = 796 且平台角标齐全', state.cards === 796 && state.badges >= 796, `cards=${state.cards} badges=${state.badges}`);
	const yt = await page.evaluate(() => {
		const chip = [...document.querySelectorAll('#video-filters .chip')].find(c => c.dataset.v === 'youtube');
		chip.click();
		return document.getElementById('count').textContent;
	});
	record('D-V-5 YouTube 筛选联动', parseInt(yt) > 0, yt);
	const title = await text(page);
	record('D-V-6 标题双语（zh 默认）', title.includes('童心岛'), title);
}

async function testDesktopBookZh(page) {
	const sel = page.locator('#datatype');
	await sel.selectOption('book');
	const state = await page.evaluate(() => {
		const vis = (id) => getComputedStyle(document.getElementById(id)).display !== 'none';
		const rows = [...document.querySelectorAll('#book-filters .filter-row')].filter(r => getComputedStyle(r).display !== 'none').map(r => r.dataset.bview);
		return {
			navtabsHidden: getComputedStyle(document.getElementById('navtabs')).display === 'none',
			chipsVisible: vis('bookview-chips'),
			bookSection: vis('book-section'),
			rows,
			bookCards: document.querySelectorAll('#book-grid .bookcell').length,
			awardCards: document.querySelectorAll('#award-grid .awardcell').length,
			themeChips: [...document.querySelectorAll('#book-filters .chip[data-bdim="theme"]')].map(c => c.textContent.trim()),
		};
	});
	record('D-B-1 tab 隐藏 / chips 显示', state.navtabsHidden && state.chipsVisible);
	record('D-B-2 书目视图行 = 年龄/语言/主题（无奖项语言）', state.rows.filter(r => r === 'books').length === 3 && !state.rows.includes('awards'), state.rows.join(','));
	record('D-B-3 绘本 451 本', state.bookCards === 451, `实际 ${state.bookCards}`);
	record('D-B-4 奖项 10 张卡片', state.awardCards === 10);
	record('D-B-5 图书专属主题 9 类（interactive 已移除）', state.themeChips.length === 9 && !state.themeChips.includes('动画'), state.themeChips.join('/'));

	// 奖项视图
	await page.click('#bv-awards');
	const awardView = await page.evaluate(() => {
		const rows = [...document.querySelectorAll('#book-filters .filter-row')].filter(r => getComputedStyle(r).display !== 'none').map(r => r.dataset.bview);
		const grid = getComputedStyle(document.getElementById('awards-grid')).display !== 'none';
		const bookGridHidden = getComputedStyle(document.getElementById('book-grid')).display === 'none';
		return { rows, grid, bookGridHidden };
	});
	record('D-B-6 奖项视图：仅奖项语言行 + 卡片墙可见', awardView.rows.length === 1 && awardView.rows[0] === 'awards' && awardView.grid && awardView.bookGridHidden);
	await page.click('#bv-books');
}

async function testDesktopEn(page) {
	await page.goto(`${target}/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.click('#lang-toggle');
	await page.waitForTimeout(400);
	const en = await page.evaluate(() => ({
		title: document.title,
		nav: document.querySelector('[data-i18n="nav_videos"]').textContent,
		brand: document.querySelector('.logo').textContent.trim(),
		leak: [...document.querySelectorAll('.site-header span, #book-filters .dim, #video-filters .dim')].filter(el => /[\u4e00-\u9fa5]/.test(el.textContent)).map(e => e.textContent),
	}));
	record('D-E-1 标题英文', /KidiIsle/.test(en.title), en.title);
	record('D-E-2 导航英文', en.nav === 'Videos', en.nav);
	record('D-E-3 顶栏无残留中文', en.leak.length === 0, en.leak.join(','));
	record('D-E-4 品牌名 KidiIsle', en.brand.includes('KidiIsle'), en.brand);
	await page.click('#lang-toggle'); // 切回中文
}

async function testVideoDetail(page) {
	await page.goto(`${target}/video/BV11341157Wz/?v=${Date.now()}`);
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
	record('V-6 标题含视频名', d.title.includes('童心岛'), d.title);
}

async function testBookDetail(page) {
	await page.goto(`${target}/book/bk-2c634c61c964/?v=${Date.now()}`);
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
	await page.goto(`${target}/award/caldecott/?v=${Date.now()}`);
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

async function testMobile(page) {
	await page.setViewportSize({ width: 375, height: 812 });
	await page.goto(`${target}/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(600);
	const video = await page.evaluate(() => ({
		noHScroll: document.documentElement.scrollWidth <= window.innerWidth + 1,
		navtabs: getComputedStyle(document.getElementById('navtabs')).display,
		chipH: Math.round(document.getElementById('bv-books').getBoundingClientRect().height),
	}));
	record('M-V-1 无横向滚动', video.noHScroll);
	const tabH = await page.evaluate(() => Math.round(document.querySelector('.navtabs a').getBoundingClientRect().height));
	record('M-V-2 tab 文字不竖排（高度正常）', tabH > 20 && tabH < 50, `${tabH}px`);
	await page.click('#datatype');
	await page.selectOption('#datatype', 'book');
	await page.waitForTimeout(300);
	const book = await page.evaluate(() => ({
		chipsShown: getComputedStyle(document.getElementById('bookview-chips')).display !== 'none',
		navtabsHidden: getComputedStyle(document.getElementById('navtabs')).display === 'none',
		noHScroll: document.documentElement.scrollWidth <= window.innerWidth + 1,
	}));
	record('M-B-1 图书模式 chips 顶栏显示', book.chipsShown);
	record('M-B-2 tab 隐藏', book.navtabsHidden);
	record('M-B-3 无横向滚动', book.noHScroll);
	await page.setViewportSize({ width: 1280, height: 800 });
}

async function testPWA(page) {
	await page.goto(`${target}/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	await page.waitForTimeout(4000);
	const pwa = await page.evaluate(async () => {
		const reg = await navigator.serviceWorker.getRegistration('/kidisle/');
		const m = await (await fetch(document.querySelector('link[rel="manifest"]').href)).json();
		return { sw: Boolean(reg?.active || reg?.installing), scope: reg?.scope || null,
			manifestIcons: m.icons?.length || 0, display: m.display };
	});
	record('P-1 SW 注册/安装', pwa.sw, pwa.swScope || '');
	record('P-2 manifest 3 图标 + standalone', pwa.manifestIcons >= 3 && pwa.display === 'standalone');
}

// ---- 主流程 ----
(async () => {
	if (LOCAL) {
		target = await startLocalServer() + '/kidisle';
		console.log(`本地模式：${target}`);
	}
	browser = await chromium.launch();
	const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
	await page.goto(`${target}/?v=${Date.now()}`);
	await page.waitForLoadState('domcontentloaded');
	try {
		await testDesktopVideoZh(page);
		await testDesktopBookZh(page);
		await testDesktopEn(page);
		await testVideoDetail(page);
		await testBookDetail(page);
		await testAwardDetail(page);
		await testMobile(page);
		await testPWA(page);
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
