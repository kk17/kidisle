// BASE_URL 规范化：保证以 / 结尾，拼接子路径才不会出现 /tinycovevideo 这类断链
const raw = import.meta.env.BASE_URL;
export const base = raw.endsWith('/') ? raw : raw + '/';

// 相对资源路径（如 books.json 里的 covers/xxx.jpg）→ 站点绝对路径
export const assetUrl = (p: string) =>
	!p || p.startsWith('http') || p.startsWith('/') ? p : base + p;
