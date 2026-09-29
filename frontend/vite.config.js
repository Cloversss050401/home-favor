import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 后端 FastAPI：本地联调走代理，避免 CORS 与跨域下载问题
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      // 后端导出的 Excel 资源（resources/exports 静态挂载）
      '/exports': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      // 用户上传资源（个人中心头像 resources/upload 静态挂载）
      '/resources': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1500,
  },
})