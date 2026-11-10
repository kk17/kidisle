// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
// GitHub Pages 组织站：仓库 tinycove.github.io → 部署在 https://tinycove.github.io/ 根路径
export default defineConfig({
	site: 'https://tinycove.github.io',
	base: '/',
});
