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
	filter_platform: { zh: '平台', en: 'Platform' },
	clear: { zh: '清空', en: 'Clear' },
	all: { zh: '全部', en: 'All' },
	empty_home: { zh: '这个组合下暂时没有视频，换个筛选试试～', en: 'No videos match this combination — try different filters.' },
	empty_creators: { zh: '这个主题下暂时没有博主～', en: 'No creators under this topic yet.' },
	creators_intro: { zh: '位博主，点进博主查看全部视频。', en: 'curated creators. Open one to see all their videos.' },
	creators_prefix: { zh: '共收录', en: 'Featuring' },
	source_label: { zh: '来源', en: 'Source' },
	source_name: { zh: '{name}', en: '{name}' },
	blogger_reason: { zh: '{reason_zh}', en: '{reason_en}' },
	videos_count: { zh: '{n} 条视频', en: '{n} videos' },
	creators_intro_full: { zh: '共收录 {n} 位博主，点进博主查看全部视频。', en: 'Featuring {n} curated creators — open one to browse all their videos.' },
	award_books_count: { zh: '{n} 本获奖绘本', en: '{n} awarded books' },
	datatype_label: { zh: '数据类型', en: 'Data type' },
	mode_video: { zh: '视频片单', en: 'Videos' },
	mode_book: { zh: '绘本书单', en: 'Picture books' },
	empty_books: { zh: '这个组合下暂时没有绘本，换个筛选试试～', en: 'No picture books match this combination — try different filters.' },
	douban_page: { zh: '豆瓣页面 ↗', en: 'Douban ↗' },
	bookview_label: { zh: '浏览方式', en: 'Browse' },
	bookview_books: { zh: '书目', en: 'Books' },
	award_lang_label: { zh: '奖项语言', en: 'Award language' },
	bookview_awards: { zh: '奖项', en: 'Awards' },
	awards_intro: { zh: '位获奖创作者的奖项与历届获奖绘本。', en: 'award programmes — open one to browse its winning books by year.' },
	awards_prefix: { zh: '共收录', en: 'Featuring' },
	award_lang_all: { zh: '全部', en: 'All' },
	award_lang_zh: { zh: '中文奖项', en: 'Chinese awards' },
	award_lang_en: { zh: '英文奖项', en: 'English awards' },
	award_lang_intl: { zh: '国际奖项', en: 'International awards' },
	award_region: { zh: '颁发地区', en: 'Region' },
	award_winners_title: { zh: '历届获奖绘本', en: 'Winning books by year' },
	award_official: { zh: '官方网站 ↗', en: 'Official site ↗' },
	book_rights: {
		zh: '图书信息引自豆瓣读书 / Goodreads，版权归原作者与出版社所有。',
		en: 'Book metadata from Douban / Goodreads. Rights belong to the original authors and publishers.',
	},
	feedback_btn: { zh: '🗣️ 反馈问题', en: '🗣️ Report an issue' },
	reason_title: { zh: '推荐理由', en: 'Why we recommend' },
	pub_info: { zh: '出版信息', en: 'Publication' },
	isbn_label: { zh: 'ISBN', en: 'ISBN' },
	publisher_label: { zh: '出版社', en: 'Publisher' },
	rating_label: { zh: '评分', en: 'Rating' },
	links_title: { zh: '链接与来源', en: 'Links & source' },
	brand_name: { zh: '童心岛', en: 'KidiIsle' },
	open_bilibili: { zh: '↗ 在 B 站打开', en: '↗ Open on Bilibili' },
	open_youtube: { zh: '↗ 在 YouTube 打开', en: '↗ Open on YouTube' },
	copy_link: { zh: '🔗 复制链接', en: '🔗 Copy link' },
	copied: { zh: '✅ 已复制', en: '✅ Copied' },
	save_kiki: { zh: '⭐ 收藏到 KikiReel', en: '⭐ Save to KikiReel' },
	episodes: { zh: '选集', en: 'Episodes' },
	watch_all_bili: { zh: '在 B 站看全部 ↗', en: 'Watch all on Bilibili ↗' },
	footer_rights: { zh: '视频版权归原 UP 主所有', en: 'Video rights belong to the original creators' },
	bilibili_home: { zh: '↗ B站主页', en: '↗ Bilibili space' },
	related: { zh: '相关推荐', en: 'Related' },
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

// 来源名（媒体/社区）的中英对照：英文态用英文媒体名或社区名
export const SOURCE_EN: Record<string, string> = {
	'社区精选': 'Community picks',
	'搜索发现': 'Search discovery',
	'官方账号': 'Official channel',
	'小花生宝藏UP主盘点': 'Xiaohuasheng top-UP list',
	'外滩教育推荐': 'The Paper education picks',
	'Common Sense Media': 'Common Sense Media',
	'TheHomeSchoolMom': 'TheHomeSchoolMom',
	'Nashville Parent': 'Nashville Parent',
	'Moms.com': 'Moms.com',
	'Greensprings School': 'Greensprings School',
	'PreKinders': 'PreKinders',
	'Action for Healthy Kids': 'Action for Healthy Kids',
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
