import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { config as loadDotenv } from 'dotenv'

// Load runner .env first, then app-home .env for generated/runtime values.
loadDotenv({ path: path.resolve(__dirname, '..', '.env') })
const appHome = (process.env.TBC_HOME || path.join(process.env.HOME, '.hpc_agent'))
  .replace(/^~(?=$|\/)/, process.env.HOME)
loadDotenv({ path: path.join(appHome, '.env') })

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    allowedHosts: true,  // Allow any host for dev tunnels
    hmr: false,  // Disable HMR — causes reload loops through tunnels on Safari iOS
    proxy: {
      '/api/events': {
        target: 'http://localhost:3100',
        changeOrigin: true,
        headers: { 'Cache-Control': 'no-transform' },
      },
      '/api': {
        target: 'http://localhost:3100',
        changeOrigin: true,
      },
    },
  },
})
