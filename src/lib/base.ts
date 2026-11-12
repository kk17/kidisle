// BASE_URL 规范化：保证以 / 结尾，拼接子路径才不会出现 /tinycovevideo 这类断链
const raw = import.meta.env.BASE_URL;
export const base = raw.endsWith('/') ? raw : raw + '/';

// 相对资源路径（如 books.json 里的 covers/xxx.jpg）→ 站点绝对路径
export const assetUrl = (p: string) =>
	!p || p.startsWith('http') || p.startsWith('/') ? p : base + p;

// ---- URL 语言前缀（RIGE-1080）----
// /zh/...、/en/... 是固定语言的真实页面（分享出去语言不变）；
// 不带前缀的旧地址（/videos/ 等）只是跳转页：按「手动选择过的语言 > 浏览器语言」跳到对应前缀。
export type UrlLang = 'zh' | 'en';
export const URL_LANGS: UrlLang[] = ['zh', 'en'];

// 每个页面的 getStaticPaths 都乘上三种前缀：zh / en / 无前缀（跳转页，由 middleware 输出）
export function withLangs<T extends { params: Record<string, string | undefined>; props?: unknown }>(paths: T[]) {
	return [undefined, ...URL_LANGS].flatMap((lang) => paths.map((p) => ({ ...p, params: { ...p.params, lang } })));
}

// 从路径解析语言前缀；无前缀返回 null
export function langOf(pathname: string): UrlLang | null {
	const seg = pathname.startsWith(base) ? pathname.slice(base.length) : pathname.replace(/^\//, '');
	const first = seg.split('/')[0];
	return (URL_LANGS as string[]).includes(first) ? (first as UrlLang) : null;
}

// 去掉 base 与语言前缀后的站内路径（如 'video/BV1xx/'）
export function pathAfterLang(pathname: string): string {
	const seg = pathname.startsWith(base) ? pathname.slice(base.length) : pathname.replace(/^\//, '');
	const lang = langOf(pathname);
	return lang ? seg.slice(lang.length + 1) : seg;
}

// 当前页面的站内链接前缀：/zh/ 或 /en/（无前缀页按 zh 处理，正常不会渲染到这里）
export const pageBase = (lang: UrlLang | null) => base + (lang ?? 'zh') + '/';
