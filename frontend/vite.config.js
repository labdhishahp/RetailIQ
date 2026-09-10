import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// In development the app calls the API on its own origin (/api/v1/...) and
// Vite proxies that to the local FastAPI server. In production the same paths
// are rewritten to the deployed FastAPI function, so no frontend code changes
// between environments.
const API_TARGET = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
    },
  },
  // `npm run preview` serves the production bundle; proxy it the same way so
  // the built app can be verified locally against a real backend.
  preview: {
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
    },
  },
})
