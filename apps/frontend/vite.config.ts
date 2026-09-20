import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// El frontend corre en localhost:3000 y proxea /api y /ws hacia el backend
// local en localhost:8000, para que el navegador solo hable con un origen.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "localhost",
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
