import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: true, // Expose to network for mobile testing
    proxy: {
      // Forward API calls during dev to FastAPI backend
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Do not rewrite path; backend expects /api/v1/...
      }
    }
  },
  build: {
    // Better Safari compatibility
    target: 'es2015',
    rollupOptions: {
      output: {
        manualChunks: undefined,
        // Ensure assets are properly named and accessible
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js'
      }
    },
    // Ensure assets are built with proper extensions
    assetsInlineLimit: 0
  },
  optimizeDeps: {
    // Force pre-bundling for Safari
    include: ['vue']
  }
})
