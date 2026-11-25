import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 前端固定跑在 2020 端口，接口统一走 /api 代理到后端
// 本地 python 直跑后端是 8001；若改用 Docker app（8000），把 target 改回 8000
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 2020,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
