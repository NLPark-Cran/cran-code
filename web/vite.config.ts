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

const MONACO_CHUNK_REGEX = /monaco-editor|@monaco-editor|y-monaco|yjs|y-protocols|lib0/;
const MERMAID_CHUNK_REGEX =
  /node_modules\/(mermaid|@mermaid-js|cytoscape|dagre-d3-es|elkjs|treemap|d3-|d3\/)/;
const VENDOR_CHUNK_REGEX =
  /node_modules\/(react|react-dom|react-router-dom|scheduler)\//;

// https://vite.dev/config/
export default defineConfig({
  base: "/",
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
    alias: [
      // Bare `shiki` (streamdown's code block) → trimmed language registry.
      // Subpath imports (shiki/core, shiki/langs/*, shiki/themes/*) untouched.
      {
        find: /^shiki$/,
        replacement: path.resolve(__dirname, "./src/lib/shiki-trimmed.ts"),
      },
      { find: "@", replacement: path.resolve(__dirname, "./src") },
      {
        find: "@ai-elements",
        replacement: path.resolve(__dirname, "./src/components/ai-elements"),
      },
    ],
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return;
          if (MONACO_CHUNK_REGEX.test(id)) {
            return "monaco";
          }
          // Mermaid and its heavy layout deps — only reachable via dynamic import.
          if (MERMAID_CHUNK_REGEX.test(id)) {
            return "mermaid";
          }
          if (VENDOR_CHUNK_REGEX.test(id)) {
            return "vendor";
          }
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
