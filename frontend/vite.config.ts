import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

// Where the dev server forwards `/api`. In the container the API is reachable
// as `backend`; locally it is the uvicorn process on 8000.
const API_PROXY_TARGET = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: API_PROXY_TARGET,
        changeOrigin: true
      }
    },
    /**
     * Vite rejects a request whose Host header is not the local origin, which is
     * the right default (it blocks DNS rebinding against a dev server). A hosted
     * preview reaches it through a generated hostname, so those hosts are listed
     * here instead of switching the protection off with `allowedHosts: true`.
     */
    allowedHosts: (process.env.VITE_DEV_ALLOWED_HOSTS || '')
      .split(',')
      .map((host) => host.trim())
      .filter(Boolean)
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  build: {
    target: 'esnext',
    rollupOptions: {
      output: {
        // ডাইনামিক ফাংশন ব্যবহার করায় কোনো প্যাকেজ রেজোলিউশন ফেইল করবে না
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('react-dom') || id.includes('react-router-dom')) {
              return 'vendor-react';
            }
            if (id.includes('@tanstack') || id.includes('axios')) {
              return 'vendor-query';
            }
            if (id.includes('@radix-ui') || id.includes('lucide-react')) {
              return 'vendor-ui';
            }
          }
        }
      }
    }
  }
});
