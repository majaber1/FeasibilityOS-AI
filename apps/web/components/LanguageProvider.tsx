"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  DEFAULT_LOCALE,
  Locale,
  dictionaries,
  dir,
} from "@/lib/dictionaries";

type Ctx = {
  locale: Locale;
  setLocale: (l: Locale) => void;
  toggle: () => void;
  t: (typeof dictionaries)[Locale];
};

const LanguageContext = createContext<Ctx | null>(null);

const STORAGE_KEY = "sb.locale";

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);

  // Restore persisted choice on mount.
  useEffect(() => {
    const saved = (typeof window !== "undefined" &&
      (localStorage.getItem(STORAGE_KEY) as Locale | null)) || null;
    if (saved === "ar" || saved === "en") {
      setLocaleState(saved);
    }
  }, []);

  // Keep <html> lang/dir and storage in sync.
  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = locale;
      document.documentElement.dir = dir(locale);
    }
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, locale);
    }
  }, [locale]);

  const value = useMemo<Ctx>(
    () => ({
      locale,
      setLocale: setLocaleState,
      toggle: () => setLocaleState((prev) => (prev === "ar" ? "en" : "ar")),
      t: dictionaries[locale],
    }),
    [locale],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): Ctx {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within LanguageProvider");
  return ctx;
}
