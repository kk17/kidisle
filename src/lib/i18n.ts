// 站点 UI 中英切换（内容本身保持原语言）
// 用法：页面元素标 data-i18n="key"，标签元素标 data-tag（dim + id），
// 本模块在客户端切换并记忆偏好；默认中文（服务端渲染态）。

export type Lang = 'zh' | 'en';

export const UI: Record<string, { zh: string; en: string }> = {
	nav_videos: { zh: '视频', en: 'Videos' },
	nav_creators: { zh: '博主', en: 'Creators' },
	filter_age: { zh: '年龄段', en: 'Age' },
	filter_language: { zh: '语言', en: 'Language' },
	filter_theme: { zh: '主题', en: 'Topic' },
	clear: { zh: '清空', en: 'Clear' },
	empty_home: { zh: '这个组合下暂时没有视频，换个筛选试试～', en: 'No videos match this combination — try different filters.' },
	empty_creators: { zh: '这个主题下暂时没有博主～', en: 'No creators under this topic yet.' },
	creators_intro: { zh: '位博主，点进博主查看全部视频。', en: 'curated creators. Open one to see all their videos.' },
	creators_prefix: { zh: '共收录', en: 'Featuring' },
	videos_count: { zh: '{n} 条视频', en: '{n} videos' },
	source_label: { zh: '来源', en: 'Source' },
	open_bilibili: { zh: '↗ 在 B 站打开', en: '↗ Open on Bilibili' },
	open_youtube: { zh: '↗ 在 YouTube 打开', en: '↗ Open on YouTube' },
	copy_link: { zh: '🔗 复制链接', en: '🔗 Copy link' },
	copied: { zh: '✅ 已复制', en: '✅ Copied' },
	save_kiki: { zh: '⭐ 收藏到 KikiReel', en: '⭐ Save to KikiReel' },
	episodes: { zh: '选集', en: 'Episodes' },
	episodes_total: { zh: '共 {n} 集', en: '{n} episodes' },
	episodes_more: { zh: '，显示前 {m} 集', en: ', showing first {m}' },
	watch_all_bili: { zh: '在 B 站看全部 ↗', en: 'Watch all on Bilibili ↗' },
	footer_rights: { zh: '视频版权归原 UP 主所有', en: 'Video rights belong to the original creators' },
	creators_intro_full: {
		zh: '共收录 {n} 位博主，点进博主查看全部视频。',
		en: 'Featuring {n} curated creators — open one to see all their videos.',
	},
	bilibili_home: { zh: '↗ B站主页', en: '↗ Bilibili space' },
	source_label: { zh: '来源', en: 'Source' },
	related: { zh: '相关推荐', en: 'Related' },
	match_count: { zh: '{s} / {t}', en: '{s} / {t}' },
	back_to_creators: { zh: '← 返回博主列表', en: '← All creators' },
	tip_bili: {
		zh: '视频通过 B 站官方播放器播放，版权归原 UP 主所有。',
		en: 'Played via the official Bilibili embed. Rights belong to the original creator.',
	},
	tip_youtube: {
		zh: '视频通过 YouTube 官方嵌入播放，版权归原创作者所有。',
		en: 'Played via the official YouTube embed. Rights belong to the original creator.',
	},
};

export function getLang(): Lang {
	return (localStorage.getItem('kidisle-lang') as Lang) || 'zh';
}

export function setLang(lang: Lang) {
	localStorage.setItem('kidisle-lang', lang);
}

export function t(key: string, lang: Lang, vars?: Record<string, string | number>): string {
	const entry = UI[key];
	if (!entry) return key;
	let text = entry[lang] ?? entry.zh;
	if (vars) for (const [k, v] of Object.entries(vars)) text = text.replace(`{${k}}`, String(v));
	return text;
}
