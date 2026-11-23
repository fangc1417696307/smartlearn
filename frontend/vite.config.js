import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 后端地址默认 8001；本地调试多实例时可用 VITE_BACKEND 覆盖
const backend = process.env.VITE_BACKEND || 'http://127.0.0.1:8001'
const wsBackend = backend.replace(/^http/, 'ws')

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: backend,
        changeOrigin: true,
      },
      // 聊天 / 在线状态 WebSocket（PPT P06）：转发到后端长连接
      '/ws': {
        target: wsBackend,
        ws: true,
      },
    },
  },
})
