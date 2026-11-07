// @ts-check
import { defineConfig } from 'astro/config';
import { AstroPWAIntegration } from '@vite-pwa/astro';

// https://astro.build/config
// GitHub Pages 项目站：部署在 https://kk17.github.io/kidisle/ 子路径下
export default defineConfig({
	site: 'https://kk17.github.io',
	base: '/kidisle',
	integrations: [
		AstroPWAIntegration({
			// PWA：可安装 + 离线可用（Workbox generateSW 预缓存全部构建产物）
			registerType: 'autoUpdate',
			includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
			manifest: {
				name: '童心岛 KidiIsle',
				short_name: '童心岛',
				description: '为孩子精选的儿童视频与绘本，按年龄段、语言、主题筛选。',
				lang: 'zh-CN',
				start_url: '/kidisle/',
				scope: '/kidisle/',
				display: 'standalone',
				theme_color: '#38bdf8',
				background_color: '#f0f9ff',
				icons: [
					{ src: '/kidisle/pwa-192.png', sizes: '192x192', type: 'image/png' },
					{ src: '/kidisle/pwa-512.png', sizes: '512x512', type: 'image/png' },
					{ src: '/kidisle/pwa-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
				],
			},
			workbox: {
				// 注意：blogger/<UP主>/ 目录名含单引号/方括号/中文，
				// Workbox 生成的预缓存清单未转义会导致 sw.js 求值崩溃——
				// 因此预缓存只收安全路径，页面导航走 NetworkFirst 运行时缓存。
				globPatterns: [
					'_astro/**/*.{js,css,woff2}',
					'*.html',
					'favicon.svg',
					'pwa-192.png',
					'pwa-512.png',
					'pwa-maskable-512.png',
					'apple-touch-icon.png',
				],
				runtimeCaching: [
					{
						// 页面导航：网络优先（内容随部署更新），离线回退缓存
						urlPattern: ({ request }) => request.mode === 'navigate',
						handler: 'NetworkFirst',
						options: {
							cacheName: 'kidisle-pages',
							networkTimeoutSeconds: 3,
							expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 30 },
							cacheableResponse: { statuses: [200] },
						},
					},
					{
						// 封面图片：缓存优先（自托管静态资源）
						urlPattern: /\/kidisle\/covers\/.*/i,
						handler: 'CacheFirst',
						options: {
							cacheName: 'kidisle-covers',
							expiration: { maxEntries: 800, maxAgeSeconds: 60 * 60 * 24 * 90 },
							cacheableResponse: { statuses: [200] },
						},
					},
					{
						// 哈希命名的静态资源：缓存优先
						urlPattern: /\/kidisle\/_astro\/.*/i,
						handler: 'CacheFirst',
						options: {
							cacheName: 'kidisle-assets',
							expiration: { maxEntries: 100, maxAgeSeconds: 60 * 60 * 24 * 90 },
							cacheableResponse: { statuses: [200] },
						},
					},
				],
			},
		}),
	],
});
