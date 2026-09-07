"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";

const services = [
  { href: "/tools/feasibility", icon: "📊", code: "01", title: { ar: "دراسة الجدوى V2", en: "Feasibility Study V2" }, desc: { ar: "محرك ذكاء اصطناعي متعدد الوكلاء", en: "Multi-agent AI decision engine" } },
  { href: "/tools/financial", icon: "💰", code: "02", title: { ar: "التحليل المالي", en: "Financial Analysis" }, desc: { ar: "ROI و NPV و IRR وتحليل الحساسية", en: "ROI, NPV, IRR, and sensitivity analysis" } },
  { href: "/tools/funding", icon: "🏦", code: "03", title: { ar: "مطابقة التمويل", en: "Funding Matcher" }, desc: { ar: "مطابقة شفافة مع البرامج السعودية", en: "Transparent matching with Saudi programs" } },
  { href: "/tools/opportunities", icon: "🎯", code: "04", title: { ar: "رادار الفرص", en: "Opportunity Radar" }, desc: { ar: "فرص مصنّفة حسب القطاع والمخاطر", en: "Opportunities by sector and risk" } },
  { href: "/tools/ideas", icon: "💡", code: "05", title: { ar: "بنك الأفكار", en: "Idea Bank" }, desc: { ar: "أفكار مشاريع رؤية 2030", en: "Vision 2030 project ideas" } },
  { href: "/tools/proposal", icon: "📝", code: "06", title: { ar: "منشئ العروض", en: "Proposal Builder" }, desc: { ar: "عروض تجارية احترافية بالعربية والإنجليزية", en: "Professional proposals in Arabic & English" }, comingSoon: true },
];

const journey = [
  { step: "1", ar: "ملف المنشأة", en: "Business Profile" },
  { step: "2", ar: "دراسة الجدوى", en: "Feasibility Study" },
  { step: "3", ar: "القرار المالي", en: "Financial Decision" },
  { step: "4", ar: "التمويل", en: "Funding" },
  { step: "5", ar: "العرض / حزمة المستثمر", en: "Proposal / Investor Package" },
];

export default function HomePage() {
  const { t, locale } = useLanguage();
  const ar = locale === "ar";

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-50 via-white to-white">
        <div className="pointer-events-none absolute inset-0 opacity-[0.07] [background:radial-gradient(circle_at_85%_15%,theme(colors.gold.500),transparent_45%)]" />
        <div className="container-page relative py-20 sm:py-28">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-brand-200 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-wide text-brand-700">
            {t.tagline}
          </p>
          <h1 className="max-w-3xl text-4xl font-bold leading-[1.15] tracking-tight text-ink-900 sm:text-5xl lg:text-6xl">
            {ar ? "من فكرة المشروع إلى جاهزية الاستثمار" : "From business idea to investment-ready"}
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink-600">
            {ar
              ? "منصة سعودية متكاملة تضم أدوات مستقلة لدراسة الجدوى والتحليل المالي ومطابقة التمويل وإعداد العروض — كل أداة تعمل بشكل مستقل أو مرتبطة بسياق مشروعك."
              : "An integrated Saudi platform with independent tools for feasibility studies, financial analysis, funding matching, and proposal building — each tool works standalone or linked to your business context."}
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <Link
              href="/tools"
              className="rounded-lg bg-brand-600 px-6 py-3 font-medium text-white shadow-card transition hover:bg-brand-700 hover:shadow-card-hover"
            >
              {ar ? "استعرض الأدوات" : "Explore tools"}
            </Link>
            <Link
              href="/projects"
              className="rounded-lg border border-slate-300 bg-white px-6 py-3 font-medium text-ink-800 transition hover:border-brand-500 hover:text-brand-600"
            >
              {ar ? "ابدأ دراسة جدوى ذكية" : "Start an AI feasibility study"}
            </Link>
          </div>
        </div>
      </section>

      {/* Journey */}
      <section className="border-y border-slate-200 bg-slate-50">
        <div className="container-page py-12">
          <h2 className="text-center text-xl font-bold text-ink-900">{ar ? "رحلة المنصة" : "Platform journey"}</h2>
          <p className="mt-2 text-center text-sm text-ink-600">{ar ? "كل خطوة مستقلة — استخدمها بالترتيب أو اختر ما تحتاجه" : "Each step is independent — use them in order or pick what you need"}</p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            {journey.map((j, i) => (
              <div key={j.step} className="flex items-center gap-3">
                <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-card">
                  <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-100 text-xs font-bold text-brand-700">{j.step}</span>
                  <span className="text-sm font-semibold text-ink-800">{ar ? j.ar : j.en}</span>
                </div>
                {i < journey.length - 1 && <span className="text-ink-400">→</span>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Services grid */}
      <section className="container-page py-16">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-ink-900">{ar ? "أدوات المنصة" : "Platform tools"}</h2>
            <p className="mt-2 text-sm text-ink-600">{ar ? "كل أداة مستقلة ويمكن استخدامها بشكل منفرد" : "Each tool is independent and can be used standalone"}</p>
          </div>
          <Link href="/tools" className="text-sm font-bold text-brand-600 hover:text-brand-700">{ar ? "عرض الكل" : "View all"}</Link>
        </div>
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {services.map((s) => (
            <div key={s.href} className="relative">
              {"comingSoon" in s && s.comingSoon && (
                <span className="absolute end-3 top-3 z-10 rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-bold text-amber-800">
                  {ar ? "قريبًا" : "Coming soon"}
                </span>
              )}
              <Link
                href={s.href}
                className={`group block rounded-2xl border border-slate-200 bg-white p-6 shadow-card transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-card-hover ${"comingSoon" in s && s.comingSoon ? "pointer-events-none opacity-60" : ""}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-brand-50 text-2xl">{s.icon}</div>
                  <span className="text-[10px] font-bold tracking-[0.2em] text-ink-500">{s.code}</span>
                </div>
                <h3 className="mt-4 text-lg font-bold text-ink-900 group-hover:text-brand-700">{ar ? s.title.ar : s.title.en}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-600">{ar ? s.desc.ar : s.desc.en}</p>
                <span className="mt-4 inline-block text-brand-600 transition group-hover:translate-x-1 rtl:group-hover:-translate-x-1">→</span>
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* Investors */}
      <section className="border-y border-brand-800 bg-gradient-to-br from-brand-800 via-brand-700 to-brand-900">
        <div className="container-page flex flex-col items-start justify-between gap-6 py-14 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-2xl font-bold text-white">{t.investors.title}</h2>
            <p className="mt-2 max-w-xl text-sm text-white/80">{t.investors.body}</p>
          </div>
          <Link
            href="/tools/opportunities"
            className="shrink-0 rounded-lg bg-gold-500 px-6 py-3 font-medium text-brand-900 shadow-card transition hover:bg-gold-400"
          >
            {t.investors.cta}
          </Link>
        </div>
      </section>

      {/* Independence callout */}
      <section className="container-page py-16">
        <div className="rounded-2xl border border-brand-200 bg-brand-50 p-8 sm:p-10">
          <h2 className="text-2xl font-bold text-brand-900">{ar ? "كل أداة مستقلة" : "Every tool is independent"}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-brand-800">
            {ar
              ? "لا تحتاج لإكمال دراسة الجدوى لاستخدام التحليل المالي. ولا تحتاج لنتائج التأهيل لبدء مطابقة التمويل. كل أداة تعمل بشكل مستقل — ولكن عندما تربطها بمشروعك، تتشارك السياق التجاري تلقائيًا."
              : "You don't need to complete a feasibility study to use financial analysis. And you don't need qualification results to start funding matching. Each tool works independently — but when you link them to your business, they share context automatically."}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href="/businesses" className="rounded-lg bg-brand-600 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-700">
              {ar ? "إدارة أعمالي" : "Manage my businesses"}
            </Link>
            <Link href="/tools" className="rounded-lg border border-brand-400 px-5 py-3 text-sm font-semibold text-brand-800 hover:bg-brand-100">
              {ar ? "تصفح الأدوات" : "Browse tools"}
            </Link>
          </div>
        </div>
      </section>

      {/* Status strip */}
      <section className="border-b border-slate-200 bg-slate-50">
        <div className="container-page py-10">
          <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
            <h3 className="font-semibold text-amber-800">{t.status.title}</h3>
            <p className="mt-1 text-sm text-amber-700">{t.status.body}</p>
          </div>
        </div>
      </section>
    </div>
  );
}
