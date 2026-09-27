import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Loopback only. Offline console — must never bind a public interface, never a CDN.
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, strictPort: true },
  preview: { host: "127.0.0.1", port: 4173, strictPort: true },
});
