/**
 * Trimmed replacement for the bare `shiki` specifier (aliased in vite.config.ts).
 *
 * streamdown's code block imports { createHighlighter, bundledLanguages } from
 * "shiki", which statically pulls the full ~200-language registry and makes
 * Rollup emit a chunk per language (~100+ chunks, multi-MB). This shim
 * resolves only the common languages/themes via dynamic imports, so the build
 * ships the trimmed set only. Unknown language names degrade to plain text
 * instead of breaking the build.
 */
import { createHighlighterCore } from "shiki/core";

const shellscript = () => import("shiki/langs/shellscript");
const javascript = () => import("shiki/langs/javascript");
const typescript = () => import("shiki/langs/typescript");
const python = () => import("shiki/langs/python");
const json = () => import("shiki/langs/json");
const yaml = () => import("shiki/langs/yaml");
const markdown = () => import("shiki/langs/markdown");
const xml = () => import("shiki/langs/xml");

/** Language-name subset compatible with shiki's bundledLanguages registry. */
export const bundledLanguages: Record<string, () => Promise<unknown>> = {
  javascript,
  js: javascript,
  mjs: javascript,
  cjs: javascript,
  typescript,
  ts: typescript,
  tsx: () => import("shiki/langs/tsx"),
  jsx: () => import("shiki/langs/jsx"),
  python,
  py: python,
  json,
  jsonc: () => import("shiki/langs/jsonc"),
  yaml,
  yml: yaml,
  toml: () => import("shiki/langs/toml"),
  markdown,
  md: markdown,
  html: () => import("shiki/langs/html"),
  xml,
  svg: xml,
  css: () => import("shiki/langs/css"),
  scss: () => import("shiki/langs/scss"),
  shellscript,
  bash: shellscript,
  shell: shellscript,
  sh: shellscript,
  zsh: shellscript,
  go: () => import("shiki/langs/go"),
  rust: () => import("shiki/langs/rust"),
  java: () => import("shiki/langs/java"),
  c: () => import("shiki/langs/c"),
  cpp: () => import("shiki/langs/cpp"),
  csharp: () => import("shiki/langs/csharp"),
  sql: () => import("shiki/langs/sql"),
  dockerfile: () => import("shiki/langs/dockerfile"),
  vue: () => import("shiki/langs/vue"),
  ruby: () => import("shiki/langs/ruby"),
  php: () => import("shiki/langs/php"),
  swift: () => import("shiki/langs/swift"),
  kotlin: () => import("shiki/langs/kotlin"),
};

const THEME_MODULES: Record<string, () => Promise<unknown>> = {
  "github-light": () => import("shiki/themes/github-light"),
  "github-dark": () => import("shiki/themes/github-dark"),
  "one-light": () => import("shiki/themes/one-light"),
  "one-dark-pro": () => import("shiki/themes/one-dark-pro"),
};

type CreateHighlighterOptions = {
  themes?: unknown[];
  langs?: unknown[];
} & Record<string, unknown>;

/** Drop-in for shiki's createHighlighter, restricted to the trimmed registry. */
export const createHighlighter = (options: CreateHighlighterOptions) =>
  createHighlighterCore({
    ...options,
    themes: (options.themes ?? []).map((theme) =>
      typeof theme === "string" ? (THEME_MODULES[theme]?.() ?? []) : theme,
    ),
    langs: (options.langs ?? []).map((lang) =>
      typeof lang === "string" ? (bundledLanguages[lang]?.() ?? []) : lang,
    ),
  } as Parameters<typeof createHighlighterCore>[0]);
