import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // strictPort: if 5173 is busy, fail loudly instead of moving to a port the backend does not allow (CORS).
  server: { port: 5173, strictPort: true },
});
