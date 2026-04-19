import { fileURLToPath, URL } from 'node:url';

import { defineConfig, loadEnv } from 'vite';
import vue from '@vitejs/plugin-vue';

// Vite 只负责前端开发体验，业务别名统一收敛在这里，避免页面里出现大量相对路径跳转。
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const devProxyTarget = env.VITE_DEV_PROXY_TARGET || 'http://127.0.0.1:8000';

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      proxy: {
        /**
         * 前端默认仍使用相对地址 `/api/v1`，这里把开发态请求转发到本地 FastAPI。
         * 这样不开额外 `.env.local` 也能优先命中真实后端，而不是误打到 Vite 自己后回退 mock。
         */
        '/api': {
          target: devProxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
