import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],

    // Make VITE_API_URL available at build time
    define: {
      __API_URL__: JSON.stringify(env.VITE_API_URL || 'http://localhost:8000'),
    },

    // Dev server proxy — avoids CORS issues during local development
    server: {
      port: 5173,
      proxy: {
        // Proxy all /api/* requests to the local backend
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },

    build: {
      // Split chunks for better caching
      rollupOptions: {
        output: {
          manualChunks: (id) => {
            if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
              return 'vendor'
            }
          },
        },
      },
      // Warn if any chunk exceeds 500 kB
      chunkSizeWarningLimit: 500,
    },
  }
})
