import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import ar from "./ar";
import en from "./en";
import type { MessageKey } from "./en";

export type Lang = "en" | "ar";

const dictionaries = { en, ar };
const STORAGE_KEY = "dukkan.lang";

interface I18n {
  lang: Lang;
  dir: "ltr" | "rtl";
  setLang: (lang: Lang) => void;
  t: (key: MessageKey, vars?: Record<string, string | number>) => string;
  /** Pick the Arabic text when the UI is in Arabic and one exists. */
  pick: (english: string, arabic?: string | null) => string;
}

const I18nContext = createContext<I18n | null>(null);

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "ar") return saved;
  } catch {
    // ignore
  }
  return navigator.language.startsWith("ar") ? "ar" : "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang);
  const dir = lang === "ar" ? "rtl" : "ltr";

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = dir;
  }, [lang, dir]);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
  }, []);

  const value = useMemo<I18n>(() => {
    const messages = dictionaries[lang];
    return {
      lang,
      dir,
      setLang,
      t: (key, vars) => {
        let text: string = messages[key] ?? en[key] ?? key;
        for (const [name, v] of Object.entries(vars ?? {})) {
          text = text.replaceAll(`{${name}}`, String(v));
        }
        return text;
      },
      pick: (english, arabic) => (lang === "ar" && arabic ? arabic : english),
    };
  }, [lang, dir, setLang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  const value = useContext(I18nContext);
  if (!value) throw new Error("useI18n must be used inside I18nProvider");
  return value;
}
