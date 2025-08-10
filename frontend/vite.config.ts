import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      // Forward API calls during dev to FastAPI backend
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Do not rewrite path; backend expects /api/v1/...
      }
    }
  }
})
