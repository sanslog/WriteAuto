import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    extensions: ['.js', '.json', '.vue'],
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:21278',
    },
  },
  build: {
    outDir: 'dist',
  },
})
