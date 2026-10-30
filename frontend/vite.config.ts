import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // The API and the pin images both live on the backend.
      "/api": { target: "http://localhost:8787", changeOrigin: true },
      "/images": { target: "http://localhost:8787", changeOrigin: true },
    },
  },
});
