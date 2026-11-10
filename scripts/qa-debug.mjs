#!/usr/bin/env node
// 本地 QA 失败调试：捕获页面 console/pageerror
import { chromium } from 'playwright';
import http from 'node:http';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../dist/', import.meta.url));
const server = http.createServer((req, res) => {
	let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
	let f = root + p;
	if (f.endsWith('/')) f += 'index.html';
	try { res.writeHead(200); res.end(readFileSync(f)); } catch { res.writeHead(404); res.end(); }
});
await new Promise(r => server.listen(0, () => r()));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on('console', m => console.log('[console]', m.type(), m.text().slice(0, 150)));
page.on('pageerror', e => console.log('[pageerror]', String(e).slice(0, 200)));
page.on('requestfailed', r => console.log('[reqfail]', r.url().slice(0, 90), r.failure()?.errorText));

await page.goto('http://localhost:' + server.address().port + '/?v=' + Date.now());
await page.waitForLoadState('domcontentloaded');
await page.waitForTimeout(1500);

const sel = page.locator('#datatype');
await sel.selectOption('book');
await page.waitForTimeout(500);

const st = await page.evaluate(() => {
	const rows = [...document.querySelectorAll('#book-filters .filter-row')];
	return { rows: rows.map(r => ({ bview: r.dataset.bview, hidden: r.hidden })), grid: getComputedStyle(document.getElementById('awards-grid')).display };
});
console.log('rows:', JSON.stringify(st.rows), '| awardsGrid:', st.grid);

const bva = page.locator('#bv-awards');
try { await bva.click({ timeout: 5000 }); console.log('click OK'); } catch (e) { console.log('click ERR:', e.message.slice(0, 120)); }

await browser.close();
server.close();
process.exit(0);
