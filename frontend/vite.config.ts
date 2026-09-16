import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El backend FastAPI corre en 8756 y sirve el build de producción directamente,
// pero en modo desarrollo (npm run dev) usamos un proxy para hablar con la API.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8756",
      "/media": "http://127.0.0.1:8756",
    },
  },
  build: {
    outDir: "dist",
  },
});
