"use client";

import { usePathname } from "next/navigation";
import { Footer } from "@/components/Footer";
import { Navbar } from "@/components/Navbar";
import { useLanguage } from "@/components/LanguageProvider";

/**
 * Routes that keep the full marketing footer (landing / public content).
 * Everything else uses a compact product shell (no marketing chrome).
 */
const MARKETING_FOOTER_PREFIXES = [
  "/", // exact match handled in isExactOrChild
  "/pricing",
  "/help",
  "/about",
  "/opportunities",
  "/franchises",
  "/ideas",
  "/multazim",
  "/funding",
];

const AUTH_GATE_PREFIXES = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
];

function isExactOrChild(pathname: string, prefix: string): boolean {
  if (prefix === "/") return pathname === "/";
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

function useShellMode(pathname: string | null): "marketing" | "auth" | "app" {
  const path = pathname || "/";
  if (AUTH_GATE_PREFIXES.some((p) => isExactOrChild(path, p))) return "auth";
  if (MARKETING_FOOTER_PREFIXES.some((p) => isExactOrChild(path, p))) return "marketing";
  return "app";
}

function CompactProductFooter() {
  const { t, locale } = useLanguage();
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-slate-200 bg-white" data-testid="product-footer">
      <div className="container-page flex flex-wrap items-center justify-between gap-2 py-3 text-xs text-ink-500">
        <p>
          © {year} {t.brand}
        </p>
        <p className="text-ink-400">
          {locale === "ar" ? "مساحة عمل المنتج" : "Product workspace"}
        </p>
      </div>
    </footer>
  );
}

function AuthMinimalFooter() {
  const { t } = useLanguage();
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-slate-200 bg-white" data-testid="auth-footer">
      <div className="container-page py-3 text-center text-xs text-ink-500">
        © {year} {t.brand}
      </div>
    </footer>
  );
}

/**
 * Application chrome: marketing footer only on public pages;
 * authenticated product routes get a dense SaaS shell.
 */
export function AppChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const mode = useShellMode(pathname);

  return (
    <div
      className={
        mode === "app"
          ? "app-shell flex min-h-screen flex-col bg-slate-50"
          : mode === "auth"
            ? "auth-shell flex min-h-screen flex-col bg-slate-50"
            : "marketing-shell flex min-h-screen flex-col"
      }
      data-shell={mode}
      data-testid="app-chrome"
    >
      <Navbar dense={mode === "app"} />
      <main className={mode === "app" ? "flex-1 pb-4" : "flex-1"}>{children}</main>
      {mode === "marketing" ? <Footer /> : null}
      {mode === "app" ? <CompactProductFooter /> : null}
      {mode === "auth" ? <AuthMinimalFooter /> : null}
    </div>
  );
}
