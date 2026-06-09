import fs from "node:fs";
import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { visualizer } from "rollup-plugin-visualizer";
import { defineConfig } from "vite";
import { nodePolyfills } from "vite-plugin-node-polyfills";

const PYPROJECT_VERSION_REGEX = /^\s*version\s*=\s*"([^"]+)"/m;

function readCranCliVersion(): string {
  const fallback = process.env.CRAN_CLI_VERSION ?? "dev";
  const pyprojectPath = path.resolve(__dirname, "../pyproject.toml");

  try {
    const pyproject = fs.readFileSync(pyprojectPath, "utf8");
    const match = pyproject.match(PYPROJECT_VERSION_REGEX);
    if (match?.[1]) {
      return match[1];
    }
  } catch (error) {
    console.warn("[vite] Unable to read version", pyprojectPath, error);
  }

  return fallback;
}

const cranCliVersion = readCranCliVersion();
const shouldAnalyze = process.env.ANALYZE === "true";

// https://vite.dev/config/
export default defineConfig({
  // Use relative paths so assets work under any base path.
  base: "./",
  plugins: [
    nodePolyfills({
      include: ["path", "url"],
    }),
    react({
      babel: {
        plugins: [
          ["babel-plugin-react-compiler", {}],
        ],
      },
    }),
    tailwindcss(),
    ...(shouldAnalyze
      ? [
          visualizer({
            brotliSize: true,
            filename: "dist/bundle-report.html",
            gzipSize: true,
            open: false,
            template: "treemap",
          }),
        ]
      : []),
  ],
  define: {
    __CRAN_CLI_VERSION__: JSON.stringify(cranCliVersion),
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@ai-elements": path.resolve(__dirname, "./src/components/ai-elements"),
    },
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks: {
          monaco: ["@monaco-editor/react"],
          vendor: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
  server: {
    allowedHosts: true,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET ?? "http://127.0.0.1:5494",
        changeOrigin: true,
        ws: true, // Enable WebSocket proxy
      },
    },
  },
});
