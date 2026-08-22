import { useCallback, useEffect, useState } from "react";

/**
 * Color theme (palette) axis — orthogonal to dark mode (.dark class, managed
 * by useTheme). Applied via `data-theme` on <html>; CSS token overrides live
 * in index.css under `:root[data-theme="..."]` / `.dark[data-theme="..."]`.
 * Persisted to localStorage and pre-applied by the inline bootstrap script in
 * index.html to avoid a flash of the default palette.
 */

export type ColorTheme = "graphite" | "cinnabar" | "teal";

export const COLOR_THEME_STORAGE_KEY = "cran-color-theme";

export const COLOR_THEMES: ColorTheme[] = ["graphite", "cinnabar", "teal"];

/** Representative swatch colors for previews (light-mode primary). */
export const COLOR_THEME_SWATCH: Record<ColorTheme, string> = {
  graphite: "oklch(0.372 0.039 260)",
  cinnabar: "oklch(0.5 0.15 35)",
  teal: "oklch(0.6 0.11 185)",
};

function isColorTheme(value: string | null): value is ColorTheme {
  return value === "graphite" || value === "cinnabar" || value === "teal";
}

function getInitialColorTheme(): ColorTheme {
  if (typeof window === "undefined") return "graphite";
  const stored = window.localStorage.getItem(COLOR_THEME_STORAGE_KEY);
  return isColorTheme(stored) ? stored : "graphite";
}

export function useColorTheme(): {
  colorTheme: ColorTheme;
  setColorTheme: (next: ColorTheme) => void;
} {
  const [colorTheme, setColorThemeState] =
    useState<ColorTheme>(getInitialColorTheme);

  useEffect(() => {
    if (typeof document === "undefined") return;
    document.documentElement.setAttribute("data-theme", colorTheme);
    window.localStorage.setItem(COLOR_THEME_STORAGE_KEY, colorTheme);
  }, [colorTheme]);

  const setColorTheme = useCallback((next: ColorTheme) => {
    setColorThemeState(next);
  }, []);

  return { colorTheme, setColorTheme };
}
