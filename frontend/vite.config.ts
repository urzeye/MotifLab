import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    host: "0.0.0.0", // 允许开发服务器被外部 IP 访问，适用于云服务器环境
    proxy: {
      "/api": {
        target: "http://127.0.0.1:12398",
        changeOrigin: true,
      },
      "/output": {
        target: "http://127.0.0.1:12398",
        changeOrigin: true,
      },
    },
  },
});
