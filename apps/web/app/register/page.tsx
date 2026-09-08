"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import { login, register, saveToken } from "@/lib/api";

type RoleKey =
  | "entrepreneur"
  | "consultant"
  | "investor"
  | "franchise_owner"
  | "gov_reviewer"
  | "admin";

const ROLE_LABELS: Record<RoleKey, { ar: string; en: string }> = {
  entrepreneur: { ar: "رائد أعمال", en: "Entrepreneur" },
  consultant: { ar: "مستشار", en: "Consultant" },
  investor: { ar: "مستثمر", en: "Investor" },
  franchise_owner: { ar: "مانح امتياز", en: "Franchise Owner" },
  gov_reviewer: { ar: "مراجع حكومي", en: "Government Reviewer" },
  admin: { ar: "مدير النظام", en: "Administrator" },
};

const SELECTABLE_ROLES: RoleKey[] = [
  "entrepreneur",
  "consultant",
  "investor",
  "franchise_owner",
];

const copy = {
  ar: {
    title: "إنشاء حساب",
    name: "الاسم الكامل",
    email: "البريد الإلكتروني",
    password: "كلمة المرور (٨ أحرف على الأقل)",
    role: "نوع الحساب",
    submit: "إنشاء الحساب",
    loading: "جارٍ الإنشاء...",
    haveAccount: "لديك حساب بالفعل؟",
    login: "تسجيل الدخول",
    success: "تم إنشاء الحساب بنجاح. يمكنك الآن تسجيل الدخول باسم",
    serviceNote: "قد يُطلب تأكيد البريد الإلكتروني عند تفعيل خدمة الرسائل في المنصة.",
  },
  en: {
    title: "Create an account",
    name: "Full name",
    email: "Email",
    password: "Password (min 8 characters)",
    role: "Account type",
    submit: "Create account",
    loading: "Creating...",
    haveAccount: "Already have an account?",
    login: "Sign in",
    success: "Account created successfully. You can now sign in as",
    serviceNote: "Email confirmation may be required when email delivery is enabled for the platform.",
  },
};

export default function RegisterPage() {
  const router = useRouter();
  const { locale } = useLanguage();
  const c = copy[locale];
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [roleKey, setRoleKey] = useState<RoleKey>("entrepreneur");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdFor, setCreatedFor] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const profile = await register({
        email,
        password,
        full_name: fullName || undefined,
        role_key: roleKey,
        locale,
      });
      const session = await login(email, password);
      saveToken(session.access_token);
      setCreatedFor(profile.full_name || profile.email);
      router.push("/projects");
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

        {createdFor ? (
          <p className="mt-6 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800">
            {c.success} {createdFor}.
          </p>
        ) : (
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <label className="block text-sm">
              <span className="text-ink-700">{c.name}</span>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                data-testid="register-name"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
              />
            </label>
            <label className="block text-sm">
              <span className="text-ink-700">{c.email}</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="register-email"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
              />
            </label>
            <label className="block text-sm">
              <span className="text-ink-700">{c.password}</span>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                data-testid="register-password"
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
              />
            </label>
            <label className="block text-sm">
              <span className="text-ink-700">{c.role}</span>
              <select
                value={roleKey}
                onChange={(e) => setRoleKey(e.target.value as RoleKey)}
                className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 outline-none focus:border-brand-500"
              >
                {SELECTABLE_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABELS[r][locale]}
                  </option>
                ))}
              </select>
            </label>
            {error && (
              <p className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={busy}
              data-testid="register-submit"
              className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {busy ? c.loading : c.submit}
            </button>
          </form>
        )}

        <p className="mt-6 text-sm text-ink-700">
          {c.haveAccount}{" "}
          <Link href="/login" className="font-medium text-brand-600 hover:underline">
            {c.login}
          </Link>
        </p>
        <p className="mt-4 text-xs text-ink-500">{c.serviceNote}</p>
      </div>
    </main>
  );
}
