import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // 把前端发出的 /api 开头的请求转发到本机 Flask。
    // 这样前端代码里只写 /api/xxx 就够了：浏览器请求的是自己这个域，不存在跨域问题，
    // 后端也就不需要额外安装跨域中间件。
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
    },
  },
})
