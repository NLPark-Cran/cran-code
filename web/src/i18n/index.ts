import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import enAuth from "./en/auth";
import enChat from "./en/chat";
import enCommon from "./en/common";
import enNav from "./en/nav";
import enProject from "./en/project";
import enProviders from "./en/providers";
import enSessions from "./en/sessions";
import enSettings from "./en/settings";
import enTeams from "./en/teams";
import enTools from "./en/tools";
import enUsage from "./en/usage";
import zhAuth from "./zh/auth";
import zhChat from "./zh/chat";
import zhCommon from "./zh/common";
import zhNav from "./zh/nav";
import zhProject from "./zh/project";
import zhProviders from "./zh/providers";
import zhSessions from "./zh/sessions";
import zhSettings from "./zh/settings";
import zhTeams from "./zh/teams";
import zhTools from "./zh/tools";
import zhUsage from "./zh/usage";

export const LANG_STORAGE_KEY = "cran_lang";

export type Language = "zh" | "en";

export const resources = {
  zh: {
    common: zhCommon,
    auth: zhAuth,
    nav: zhNav,
    teams: zhTeams,
    providers: zhProviders,
    settings: zhSettings,
    project: zhProject,
    chat: zhChat,
    sessions: zhSessions,
    tools: zhTools,
    usage: zhUsage,
  },
  en: {
    common: enCommon,
    auth: enAuth,
    nav: enNav,
    teams: enTeams,
    providers: enProviders,
    settings: enSettings,
    project: enProject,
    chat: enChat,
    sessions: enSessions,
    tools: enTools,
    usage: enUsage,
  },
} as const;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    // Chinese is the default: unknown/unsupported locales resolve to zh,
    // while English doubles as the key-level fallback catalog for zh.
    fallbackLng: { default: ["zh"], zh: ["en", "zh"] },
    supportedLngs: ["zh", "en"],
    nonExplicitSupportedLngs: true,
    load: "languageOnly",
    defaultNS: "common",
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: LANG_STORAGE_KEY,
      // Persistence is handled manually in setLanguage().
      caches: [],
    },
    interpolation: { escapeValue: false },
    returnNull: false,
  });

/** Current language, normalized to a supported code. */
export function getLanguage(): Language {
  return i18n.resolvedLanguage?.startsWith("zh") ? "zh" : "en";
}

/** Switch language instantly (no reload) and persist the choice. */
export function setLanguage(lang: Language): void {
  i18n.changeLanguage(lang).catch((error: unknown) => {
    console.error("[i18n] changeLanguage failed:", error);
  });
  try {
    localStorage.setItem(LANG_STORAGE_KEY, lang);
  } catch {
    // localStorage unavailable (private mode, etc.) — ignore.
  }
}

/** Translation key for a team/project member role. */
export function roleKey(role: string): string {
  switch (role) {
    case "owner":
      return "common:roleOwner";
    case "admin":
      return "common:roleAdmin";
    default:
      return "common:roleMember";
  }
}

function syncDocumentMeta(): void {
  if (typeof document === "undefined") return; // SSR / test environment
  const lang = getLanguage();
  document.documentElement.lang = lang === "zh" ? "zh-CN" : "en";
  document.title = i18n.t("common:brandName");
}

i18n.on("languageChanged", syncDocumentMeta);
syncDocumentMeta();

export default i18n;
