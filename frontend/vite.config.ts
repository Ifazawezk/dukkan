import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the API runs on its own port; the proxy keeps everything on
// one origin so the browser never needs CORS. Override with DUKKAN_API_URL.
const apiTarget = process.env.DUKKAN_API_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
      "/docs": { target: apiTarget, changeOrigin: true },
      "/openapi.json": { target: apiTarget, changeOrigin: true },
    },
  },
  build: {
    chunkSizeWarningLimit: 900,
  },
});
