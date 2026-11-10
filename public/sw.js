/* 童心湾 Service Worker（手写极简版）
 * 策略：
 * - 页面导航：NetworkFirst（3s 超时回退缓存），离线可回访已浏览页面
 * - 封面图片：CacheFirst（自托管静态资源，90 天）
 * - 构建资源（_astro/ 哈希文件名）：CacheFirst
 * - 其他同源 GET：NetworkFirst
 * 版本号变更时 activate 清理旧缓存
 */
const VERSION = 'v2026-11-11-r2'; // URL 方案重构（RIGE-1021）：/videos/ /books/ /awards/ 真实路径
const PAGES_CACHE = `tinycove-pages-${VERSION}`;
const COVERS_CACHE = `tinycove-covers-${VERSION}`;
const ASSETS_CACHE = `tinycove-assets-${VERSION}`;
const NAV_TIMEOUT_MS = 3000;

self.addEventListener('install', (event) => {
	event.waitUntil((async () => {
		try {
			const cache = await caches.open(PAGES_CACHE);
			// 根路径是重定向页：离线首访时直接落地视频片单（review 2026-11-11 建议）
			await cache.addAll(['./', './videos/']);
		} catch (e) { /* 首屏预缓存失败不阻塞安装 */ }
		await self.skipWaiting();
	})());
});

self.addEventListener('activate', (event) => {
	event.waitUntil((async () => {
		const keep = new Set([PAGES_CACHE, COVERS_CACHE, ASSETS_CACHE]);
		const names = await caches.keys();
		await Promise.all(names.filter((n) => !keep.has(n)).map((n) => caches.delete(n)));
		await self.clients.claim();
	})());
});

async function networkFirst(request, cacheName, timeoutMs) {
	const cache = await caches.open(cacheName);
	try {
		const fresh = await Promise.race([
			fetch(request),
			new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), timeoutMs)),
		]);
		if (fresh && fresh.ok) cache.put(request, fresh.clone());
		return fresh;
	} catch (e) {
		const cached = await cache.match(request);
		if (cached) return cached;
		throw e;
	}
}

async function cacheFirst(request, cacheName) {
	const cache = await caches.open(cacheName);
	const cached = await cache.match(request);
	if (cached) return cached;
	const fresh = await fetch(request);
	if (fresh && fresh.ok) cache.put(request, fresh.clone());
	return fresh;
}

self.addEventListener('fetch', (event) => {
	const req = event.request;
	if (req.method !== 'GET') return;
	let url;
	try { url = new URL(req.url); } catch { return; }
	if (url.origin !== self.location.origin) return;

	if (req.mode === 'navigate') {
		event.respondWith(networkFirst(req, PAGES_CACHE, NAV_TIMEOUT_MS).catch(() => caches.match(url.pathname)));
		return;
	}
	if (url.pathname.includes('/covers/')) {
		event.respondWith(cacheFirst(req, COVERS_CACHE).catch(() => fetch(req)));
		return;
	}
	if (url.pathname.includes('/_astro/')) {
		event.respondWith(cacheFirst(req, ASSETS_CACHE).catch(() => fetch(req)));
		return;
	}
	// 其余同源静态资源（图标/manifest 等）
	event.respondWith(networkFirst(req, ASSETS_CACHE, NAV_TIMEOUT_MS).catch(() => fetch(req)));
});
