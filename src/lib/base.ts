// BASE_URL 规范化：保证以 / 结尾，拼接子路径才不会出现 /kidislevideo 这类断链
const raw = import.meta.env.BASE_URL;
export const base = raw.endsWith('/') ? raw : raw + '/';
