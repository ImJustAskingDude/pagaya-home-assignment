import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  cacheDir: ".vite",
  plugins: [react()],
  server: {
    port: 5173,
  },
});
