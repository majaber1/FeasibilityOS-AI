"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { clearToken, getToken, me } from "@/lib/api";
import { useRouter } from "next/navigation";

export function Navbar() {
  const { t, locale, toggle } = useLanguage();
  const [signedIn, setSignedIn] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    async function refreshAuth() {
      const token = getToken();
      if (!token) return setSignedIn(false);
      try {
        await me(token);
        setSignedIn(true);
      } catch {
        clearToken();
        setSignedIn(false);
      }
    }
    void refreshAuth();
    window.addEventListener("sb-auth-change", refreshAuth);
    return () => window.removeEventListener("sb-auth-change", refreshAuth);
  }, []);

  const links = [
    { href: "/dashboard", label: locale === "ar" ? "لوحة التحكم" : "Dashboard" },
    { href: "/businesses", label: locale === "ar" ? "أعمالي" : "My Businesses" },
    { href: "/tools", label: locale === "ar" ? "الأدوات" : "Tools" },
    { href: "/opportunities", label: t.nav.opportunities },
    { href: "/pricing", label: t.nav.pricing },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
      <nav className="container-page flex h-16 items-center justify-between gap-4" aria-label={locale === "ar" ? "التنقل الرئيسي" : "Primary navigation"}>
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-brand-600 to-brand-800 font-bold text-white shadow-card">
            {locale === "ar" ? "س" : "S"}
          </span>
          <span className="text-lg font-semibold tracking-tight text-ink-900">{t.brand}</span>
        </Link>

        <ul className="hidden items-center gap-7 text-sm font-medium text-ink-600 xl:flex">
          {links.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="transition-colors hover:text-brand-600">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-2">
          <button
            onClick={toggle}
            aria-label="Switch language"
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-ink-700 transition-colors hover:border-brand-500 hover:text-brand-600"
          >
            {locale === "ar" ? "English" : "العربية"}
          </button>
          {signedIn ? (
            <>
              <Link href="/account" className="hidden rounded-md px-3 py-1.5 text-sm font-medium text-ink-700 hover:text-brand-600 sm:inline-block">
                {locale === "ar" ? "حسابي" : "My account"}
              </Link>
              <button
                onClick={() => { clearToken(); setSignedIn(false); router.push("/"); router.refresh(); }}
                className="rounded-md bg-slate-100 px-4 py-1.5 text-sm font-medium text-ink-700 hover:bg-slate-200"
              >
                {locale === "ar" ? "خروج" : "Log out"}
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="hidden rounded-md px-3 py-1.5 text-sm font-medium text-ink-700 hover:text-brand-600 sm:inline-block">
                {t.nav.login}
              </Link>
              <Link href="/register" className="rounded-md bg-brand-600 px-4 py-1.5 text-sm font-medium text-white shadow-card transition-colors hover:bg-brand-700">
                {t.nav.register}
              </Link>
            </>
          )}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="grid h-9 w-9 place-items-center rounded-lg border border-slate-200 text-ink-600 xl:hidden"
            aria-label="Menu"
          >
            {mobileOpen ? "✕" : "☰"}
          </button>
        </div>
      </nav>

      {mobileOpen && (
        <div className="border-t border-slate-100 bg-white px-4 pb-4 xl:hidden">
          <ul className="space-y-1 py-2">
            {links.map((l) => (
              <li key={l.href}>
                <Link href={l.href} onClick={() => setMobileOpen(false)} className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink-700 hover:bg-brand-50 hover:text-brand-700">
                  {l.label}
                </Link>
              </li>
            ))}
            <li className="border-t border-slate-100 pt-2">
              <Link href="/tools/funding" onClick={() => setMobileOpen(false)} className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink-700 hover:bg-brand-50">
                {t.nav.funding}
              </Link>
            </li>
            <li>
              <Link href="/tools/qualification" onClick={() => setMobileOpen(false)} className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink-700 hover:bg-brand-50">
                {locale === "ar" ? "التأهيل" : "Qualification"}
              </Link>
            </li>
            <li>
              <Link href="/help" onClick={() => setMobileOpen(false)} className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink-700 hover:bg-brand-50">
                {t.nav.help}
              </Link>
            </li>
          </ul>
        </div>
      )}

      <nav className="container-page flex gap-1 overflow-x-auto pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden xl:hidden" aria-label={locale === "ar" ? "روابط المنتجات" : "Product links"}>
        {links.slice(0, 4).map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold text-ink-600 transition hover:bg-brand-50 hover:text-brand-700"
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
