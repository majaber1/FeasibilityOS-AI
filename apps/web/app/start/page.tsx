"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import { getToken, submitQuickIdeaCheck, type QuickIdeaCheckResult, type QuickIdeaCheckStatus } from "@/lib/api";

const copy = {
  ar: {
    title: "لدي فكرة مشروع",
    subtitle: "اكتب فكرتك بجملة واحدة، ونبدأ لك دراسة دائمة تُبنى عليها الأدلة والافتراضات لاحقًا.",
    loginRequired: "يلزم تسجيل الدخول لبدء دراسة.",
    goLogin: "تسجيل الدخول",
    idea: "الفكرة",
    ideaPlaceholder: "مثال: أنا أفكر بمشروع حضانة أطفال في الرياض",
    capital: "رأس المال التقديري (ر.س)",
    city: "المدينة",
    customerSegment: "العميل المستهدف",
    goal: "الهدف",
    submit: "تحقّق من الفكرة",
    submitting: "جارٍ التحقق...",
    resultTitle: "نتيجة الفحص الأولي",
    known: "معلومات معروفة",
    missing: "معلومات ناقصة",
    uncertainties: "أوجه عدم اليقين الرئيسية",
    nextStep: "الخطوة التالية الموصى بها",
    industryGuess: "القطاع المقترح",
    regulatory: "التعقيد التنظيمي المبدئي",
    openStudy: "فتح الدراسة الدائمة",
    statusLabels: {
      PROMISING: "واعدة",
      NEEDS_VALIDATION: "تحتاج تحققًا",
      INSUFFICIENT_DATA: "بيانات غير كافية",
      HIGH_UNCERTAINTY: "عدم يقين مرتفع",
    } as Record<QuickIdeaCheckStatus, string>,
    complexityLabels: { higher: "أعلى", moderate: "متوسط", lower: "أقل", unknown: "غير معروف" } as Record<string, string>,
  },
  en: {
    title: "I have a business idea",
    subtitle: "Write your idea in one sentence -- we start a permanent study that evidence and assumptions build on later.",
    loginRequired: "You need to sign in to start a study.",
    goLogin: "Sign in",
    idea: "The idea",
    ideaPlaceholder: "e.g. I'm thinking of a childcare nursery in Riyadh",
    capital: "Estimated capital (SAR)",
    city: "City",
    customerSegment: "Target customer",
    goal: "Goal",
    submit: "Check this idea",
    submitting: "Checking...",
    resultTitle: "Initial check result",
    known: "Known information",
    missing: "Missing information",
    uncertainties: "Main uncertainties",
    nextStep: "Recommended next step",
    industryGuess: "Suggested industry",
    regulatory: "Initial regulatory complexity",
    openStudy: "Open the permanent study",
    statusLabels: {
      PROMISING: "Promising",
      NEEDS_VALIDATION: "Needs validation",
      INSUFFICIENT_DATA: "Insufficient data",
      HIGH_UNCERTAINTY: "High uncertainty",
    } as Record<QuickIdeaCheckStatus, string>,
    complexityLabels: { higher: "Higher", moderate: "Moderate", lower: "Lower", unknown: "Unknown" } as Record<string, string>,
  },
};

const STATUS_STYLE: Record<QuickIdeaCheckStatus, string> = {
  PROMISING: "bg-emerald-50 text-emerald-800 border-emerald-200",
  NEEDS_VALIDATION: "bg-sky-50 text-sky-800 border-sky-200",
  INSUFFICIENT_DATA: "bg-amber-50 text-amber-800 border-amber-200",
  HIGH_UNCERTAINTY: "bg-red-50 text-red-700 border-red-200",
};

export default function QuickIdeaCheckPage() {
  const { locale } = useLanguage();
  const c = copy[locale];
  const router = useRouter();
  const token = getToken();

  const [ideaText, setIdeaText] = useState("");
  const [capital, setCapital] = useState<number | "">("");
  const [city, setCity] = useState("");
  const [customerSegment, setCustomerSegment] = useState("");
  const [goal, setGoal] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QuickIdeaCheckResult | null>(null);

  if (!token) {
    return (
      <main className="container-page py-16">
        <div className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-ink-900">{c.title}</h1>
          <p className="mt-4 text-sm text-ink-700">{c.loginRequired}</p>
          <Link href="/login?next=/start" className="mt-6 inline-flex rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700">
            {c.goLogin}
          </Link>
        </div>
      </main>
    );
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token || capital === "") return;
    setBusy(true);
    setError(null);
    try {
      const check = await submitQuickIdeaCheck(token, {
        idea_text: ideaText,
        estimated_capital: Number(capital),
        city: city || undefined,
        customer_segment: customerSegment || undefined,
        goal: goal || undefined,
      });
      setResult(check);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="container-page py-14">
      <h1 className="text-3xl font-semibold text-ink-900">{c.title}</h1>
      <p className="mt-2 max-w-2xl text-ink-700">{c.subtitle}</p>

      {error && <p role="alert" className="mt-6 max-w-2xl rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {!result && (
        <form onSubmit={onSubmit} className="mt-8 max-w-xl space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <label className="block text-sm">
            <span className="text-ink-700">{c.idea}</span>
            <textarea
              required
              minLength={3}
              rows={2}
              value={ideaText}
              onChange={(e) => setIdeaText(e.target.value)}
              placeholder={c.ideaPlaceholder}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
            />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-ink-700">{c.capital}</span>
              <input
                type="number"
                required
                min={1}
                value={capital}
                onChange={(e) => setCapital(e.target.value ? Number(e.target.value) : "")}
                className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
              />
            </label>
            <label className="block text-sm">
              <span className="text-ink-700">{c.city}</span>
              <input value={city} onChange={(e) => setCity(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500" />
            </label>
            <label className="block text-sm">
              <span className="text-ink-700">{c.customerSegment}</span>
              <input value={customerSegment} onChange={(e) => setCustomerSegment(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500" />
            </label>
            <label className="block text-sm">
              <span className="text-ink-700">{c.goal}</span>
              <input value={goal} onChange={(e) => setGoal(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500" />
            </label>
          </div>
          <button type="submit" disabled={busy} className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60">
            {busy ? c.submitting : c.submit}
          </button>
        </form>
      )}

      {result && (
        <div className="mt-8 max-w-xl space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold text-ink-900">{c.resultTitle}</h2>
            <span className={`rounded-full border px-3 py-1 text-sm font-semibold ${STATUS_STYLE[result.status]}`}>
              {c.statusLabels[result.status]}
            </span>
          </div>

          {result.industry_guess && (
            <p className="text-sm text-ink-700">
              <span className="font-medium">{c.industryGuess}:</span> {result.industry_guess} ·{" "}
              <span className="font-medium">{c.regulatory}:</span>{" "}
              {c.complexityLabels[result.regulatory_complexity_hint] ?? result.regulatory_complexity_hint}
            </p>
          )}

          {result.missing_fields.length > 0 && (
            <div>
              <p className="text-sm font-medium text-ink-700">{c.missing}</p>
              <ul className="mt-1 list-inside list-disc text-sm text-amber-800">
                {result.missing_fields.map((f) => <li key={f}>{f}</li>)}
              </ul>
            </div>
          )}

          {result.main_uncertainties.length > 0 && (
            <div>
              <p className="text-sm font-medium text-ink-700">{c.uncertainties}</p>
              <ul className="mt-1 list-inside list-disc text-sm text-ink-600">
                {result.main_uncertainties.map((u) => <li key={u}>{u}</li>)}
              </ul>
            </div>
          )}

          <p className="rounded-lg bg-brand-50 p-3 text-sm text-brand-900">{result.recommended_next_step}</p>

          <button
            onClick={() => router.push(`/projects/${result.project_id}/studies/${result.study_id}`)}
            className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700"
          >
            {c.openStudy}
          </button>
        </div>
      )}
    </main>
  );
}
