// 无语言前缀的地址 → 语言跳转页（RIGE-1080）
// 每个页面都按 zh / en / 无前缀 三份生成（见 lib/base.ts withLangs）。无前缀那份不渲染页面本体，
// 在这里直接输出一个极小的跳转页：按「手动选择过的语言 > 浏览器首选语言（中文→zh，其余→en）」
// 跳到 /zh/... 或 /en/...，保留 query 与 hash。这样旧链接、PWA start_url（/）都继续可用，
// 而地址栏里看到、分享出去的永远是带语言前缀的固定语言地址。
import { defineMiddleware } from 'astro:middleware';
import { base, langOf, pathAfterLang } from './lib/base.ts';

// 语言判定脚本：localStorage key 与 lib/i18n.ts 保持一致
export const detectLangJs = `var l=null;try{l=localStorage.getItem('tinycove-lang')||localStorage.getItem('kidisle-lang')}catch(e){}
if(l!=='zh'&&l!=='en'){var n=(navigator.languages&&navigator.languages[0])||navigator.language||'';l=/^zh\\b/i.test(n)?'zh':'en'}`;

const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');

function stub(rest: string, site: URL | undefined) {
	const target = rest === '' ? 'videos/' : rest; // 根路径直接落到视频片单，少跳一次
	const abs = (p: string) => (site ? new URL(p, site).href : p);
	const zh = `${base}zh/${target}`;
	const en = `${base}en/${target}`;
	const js = `(function(){${detectLangJs};location.replace(${JSON.stringify(base)}+l+'/'+${JSON.stringify(target)}+location.search+location.hash)})();`;
	return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>童心湾 TinyCove</title>
<meta name="robots" content="noindex, follow" />
<link rel="alternate" hreflang="zh-CN" href="${esc(abs(zh))}" />
<link rel="alternate" hreflang="en" href="${esc(abs(en))}" />
<script>${js}</script>
</head>
<body style="font-family: system-ui, sans-serif; padding: 2rem; text-align: center;">
<p><a href="${esc(zh)}">进入童心湾（中文）→</a></p>
<p><a href="${esc(en)}">Enter TinyCove (English) →</a></p>
</body>
</html>
`;
}

export const onRequest = defineMiddleware((ctx, next) => {
	const { pathname } = ctx.url;
	// 只拦页面路径：带扩展名的静态资源（/sw.js、/covers/*.jpg、/_astro/*）与已有语言前缀的路径照常放行
	if (langOf(pathname) || /\.[a-z0-9]+$/i.test(pathname) || pathname.includes('/_')) return next();
	const rest = pathAfterLang(pathname).replace(/index\.html$/, '');
	return new Response(stub(rest, ctx.site), { headers: { 'content-type': 'text/html; charset=utf-8' } });
});
