import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Guest-token API (api/guest_token_server.py) -- proxied so the browser
    // calls it same-origin, with no CORS setup on the API.
    proxy: {
      "/api": "http://127.0.0.1:8090",
    },
  },
});
