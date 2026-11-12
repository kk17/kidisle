/* 童心湾 Service Worker（手写极简版）
 * 策略：
 * - 页面导航：NetworkFirst（3s 超时回退缓存），离线可回访已浏览页面
 * - 封面图片：CacheFirst（自托管静态资源，90 天）
 * - 构建资源（_astro/ 哈希文件名）：CacheFirst
 * - 其他同源 GET：NetworkFirst
 * 版本号变更时 activate 清理旧缓存
 */
const VERSION = 'v2026-11-12-r3'; // URL 语言前缀 /zh/ /en/（RIGE-1080）
const PAGES_CACHE = `tinycove-pages-${VERSION}`;
const COVERS_CACHE = `tinycove-covers-${VERSION}`;
const ASSETS_CACHE = `tinycove-assets-${VERSION}`;
const NAV_TIMEOUT_MS = 3000;

self.addEventListener('install', (event) => {
	event.waitUntil((async () => {
		try {
			const cache = await caches.open(PAGES_CACHE);
			// 根路径是按语言跳转的小页面：两种语言的视频片单都预缓存，离线首访也能落地（RIGE-1080）
			await cache.addAll(['./', './zh/videos/', './en/videos/']);
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

// 超时只用于「有缓存时尽快回退到缓存」；没有缓存就继续等网络。
// 旧版超时后无缓存直接抛错 → respondWith 拿到 undefined → 浏览器 ERR_FAILED
// （「This site can't be reached / might be temporarily down」），首访慢页面必现（RIGE-1073）。
async function networkFirst(request, cacheName, timeoutMs) {
	const cache = await caches.open(cacheName);
	const network = fetch(request).then((fresh) => {
		if (fresh && fresh.ok) cache.put(request, fresh.clone());
		return fresh;
	});
	network.catch(() => {}); // 已回退到缓存时，避免后台网络失败变成未处理的 rejection
	try {
		return await Promise.race([
			network,
			new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), timeoutMs)),
		]);
	} catch (e) {
		const cached = await cache.match(request);
		if (cached) return cached;
		return network; // 无缓存：等网络结果（网络本身失败时由调用方兜底）
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
		event.respondWith(networkFirst(req, PAGES_CACHE, NAV_TIMEOUT_MS).catch(async () => (await caches.match(url.pathname)) || Response.error()));
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
