"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import { login, me, saveToken } from "@/lib/api";

const copy = {
  ar: {
    title: "تسجيل الدخول",
    email: "البريد الإلكتروني",
    password: "كلمة المرور",
    submit: "دخول",
    loading: "جارٍ الدخول...",
    noAccount: "ليس لديك حساب؟",
    register: "إنشاء حساب",
    forgot: "نسيت كلمة المرور؟",
    demoTitle: "تريد استكشاف المنصّة الآن؟",
    demoBody:
      "ادخل إلى لوحة عرض ببيانات توضيحية فقط. لن يتم إنشاء حساب أو حفظ أي تغييرات.",
    demoCta: "الدخول إلى العرض التجريبي",
    success: "تم تسجيل الدخول بنجاح، مرحبًا",
    serviceNote:
      "تُحمى بيانات الدخول وتُرسل إلى خدمة الحساب عبر اتصال المنصّة الآمن.",
  },
  en: {
    title: "Sign in",
    email: "Email",
    password: "Password",
    submit: "Sign in",
    loading: "Signing in...",
    noAccount: "No account yet?",
    register: "Create an account",
    forgot: "Forgot password?",
    demoTitle: "Want to explore first?",
    demoBody:
      "Open a preview dashboard with sample data only. No account is created and no changes are saved.",
    demoCta: "Continue in demo mode",
    success: "Signed in successfully, welcome",
    serviceNote:
      "Credentials are sent to the account service through the platform's secure connection.",
  },
};

export default function LoginPage() {
  const router = useRouter();
  const { locale } = useLanguage();
  const c = copy[locale];

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profileName, setProfileName] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);

    try {
      const { access_token } = await login(email, password);

      // The backend credential is now represented in the browser only by
      // the non-secret "session" hint. The real JWT is stored in the
      // HTTP-only session cookie created by the Next.js session endpoint.
      saveToken(access_token);

      const profile = await me(access_token);
      setProfileName(profile.full_name || profile.email);

      // Read redirect target only at interaction time so /login remains
      // safe to prerender during the production Next.js build.
      const requested = new URLSearchParams(
        window.location.search
      ).get("next");

      const destination =
        requested?.startsWith("/") && !requested.startsWith("//")
          ? requested
          : "/dashboard";

      router.push(destination);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="container-page py-16">
      <div className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-semibold text-ink-900">{c.title}</h1>

        {profileName ? (
          <p className="mt-6 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800">
            {c.success} {profileName}.
          </p>
        ) : (
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <label className="block text-sm">
              <span className="text-ink-700">{c.email}</span>

              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="login-email"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
              />
            </label>

            <label className="block text-sm">
              <span className="text-ink-700">{c.password}</span>

              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                data-testid="login-password"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
              />
            </label>

            {error && (
              <p
                role="alert"
                className="rounded-md bg-red-50 p-3 text-sm text-red-700"
              >
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={busy}
              data-testid="login-submit"
              className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? c.loading : c.submit}
            </button>

            <Link
              href="/forgot-password"
              className="block text-center text-sm font-medium text-brand-700 hover:underline"
            >
              {c.forgot}
            </Link>
          </form>
        )}

        <div
          className="my-6 flex items-center gap-3"
          aria-hidden="true"
        >
          <span className="h-px flex-1 bg-slate-200" />

          <span className="text-xs font-medium text-ink-400">
            {locale === "ar" ? "أو" : "OR"}
          </span>

          <span className="h-px flex-1 bg-slate-200" />
        </div>

        <section
          className="rounded-xl border border-brand-200 bg-brand-50 p-4"
          aria-labelledby="demo-access-title"
        >
          <h2
            id="demo-access-title"
            className="font-semibold text-brand-900"
          >
            {c.demoTitle}
          </h2>

          <p className="mt-1 text-sm leading-6 text-brand-900/70">
            {c.demoBody}
          </p>

          <Link
            href="/dashboard"
            className="mt-4 flex w-full items-center justify-center rounded-md border border-brand-300 bg-white px-4 py-2.5 text-sm font-bold text-brand-800 transition hover:bg-brand-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
          >
            {c.demoCta}
          </Link>
        </section>

        <p className="mt-6 text-sm text-ink-700">
          {c.noAccount}{" "}
          <Link
            href="/register"
            className="font-medium text-brand-600 hover:underline"
          >
            {c.register}
          </Link>
        </p>

        <p className="mt-4 text-xs text-ink-500">
          {c.serviceNote}
        </p>
      </div>
    </main>
  );
}