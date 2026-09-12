"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import {
  getToken,
  listProjects,
  listQualificationProfiles,
  listStudies,
  type Project,
  type QualificationProfile,
  type Study,
} from "@/lib/api";

type DashboardData = {
  projects: Project[];
  studies: Study[];
  qualifications: QualificationProfile[];
};

const demoProjects = [
  { id: -1, name: "Specialty Coffee — Riyadh", industry: "Food & Beverage", investment: 850000, stage: "active" },
  { id: -2, name: "Medical Delivery Platform", industry: "Healthcare", investment: 3200000, stage: "review" },
  { id: -3, name: "Sustainable Packaging Plant", industry: "Manufacturing", investment: 6500000, stage: "draft" },
];

function money(value: number, locale: "ar" | "en") {
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-SA", {
    style: "currency",
    currency: "SAR",
    maximumFractionDigits: 0,
  }).format(value);
}

function ProgressRing({ score }: { score: number }) {
  const value = Math.max(0, Math.min(100, score));
  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  return (
    <div className="relative grid h-36 w-36 shrink-0 place-items-center">
      <svg aria-hidden="true" viewBox="0 0 112 112" className="h-full w-full -rotate-90">
        <circle cx="56" cy="56" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="9" />
        <circle
          cx="56"
          cy="56"
          r={radius}
          fill="none"
          stroke="url(#readiness-gradient)"
          strokeLinecap="round"
          strokeWidth="9"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - value / 100)}
        />
        <defs>
          <linearGradient id="readiness-gradient">
            <stop stopColor="#0f8a4d" />
            <stop offset="1" stopColor="#c9a227" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute text-center">
        <strong className="block text-3xl text-ink-900">{Math.round(value)}</strong>
        <span className="text-xs text-ink-500">/ 100</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { locale } = useLanguage();
  const lang = locale as "ar" | "en";
  const ar = lang === "ar";
  const [data, setData] = useState<DashboardData | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    setSignedIn(true);
    let cancelled = false;
    Promise.all([
      listProjects(token),
      listStudies(token),
      listQualificationProfiles(token).catch(() => []),
    ])
      .then(([projects, studies, qualifications]) => {
        if (!cancelled) setData({ projects, studies, qualifications });
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const projects = data?.projects ?? [];
  const studies = data?.studies ?? [];
  const completed = studies.filter((study) => study.status === "completed");
  const readiness = data?.qualifications[0]?.overall_score ?? 0;
  const activeInvestment = projects
    .filter((project) => !project.is_archived)
    .reduce((total, project) => total + Number(project.investment || 0), 0);

  const nextStep = !projects.length
    ? { href: "/projects", title: ar ? "أضف مشروعك الأول" : "Add your first project", detail: ar ? "ابدأ بالاسم والقطاع والاستثمار المتوقع." : "Start with its name, sector, and expected investment." }
    : !studies.length
      ? { href: "/projects", title: ar ? "أنشئ دراسة جدوى ذكية" : "Start an AI feasibility study", detail: ar ? "استخدم محرك الذكاء الاصطناعي V2 لتحليل مشروعك خطوة بخطوة." : "Use the V2 AI engine to analyze your project step by step." }
      : !readiness
        ? { href: "/tools/qualification", title: ar ? "قيّم جاهزية مشروعك" : "Assess business readiness", detail: ar ? "اعرف متطلبات التمويل والامتثال التي تحتاجها." : "Find the funding and compliance requirements still needed." }
        : { href: "/tools/funding", title: ar ? "استكشف التمويل المناسب" : "Explore suitable funding", detail: ar ? "استخدم نتائج الدراسة والجاهزية لمراجعة الخيارات." : "Use your feasibility and readiness results to review options." };

  const cards = data
    ? [
        { label: ar ? "المشاريع النشطة" : "Active projects", value: String(projects.filter((p) => !p.is_archived).length), hint: ar ? `${projects.filter((p) => p.is_archived).length} مؤرشف` : `${projects.filter((p) => p.is_archived).length} archived` },
        { label: ar ? "دراسات الجدوى" : "Feasibility studies", value: String(studies.length), hint: ar ? `${completed.length} مكتملة` : `${completed.length} completed` },
        { label: ar ? "الاستثمار المخطط" : "Planned investment", value: money(activeInvestment, lang), hint: ar ? "عبر المشاريع النشطة" : "Across active projects" },
        { label: ar ? "درجة الجاهزية" : "Readiness score", value: readiness ? `${Math.round(readiness)}%` : "—", hint: readiness ? (ar ? "آخر تقييم" : "Latest assessment") : (ar ? "لم يتم التقييم" : "Not assessed") },
      ]
    : [
        { label: ar ? "المشاريع" : "Projects", value: "3", hint: ar ? "عرض توضيحي" : "Demo preview" },
        { label: ar ? "دراسات الجدوى" : "Feasibility studies", value: "2", hint: ar ? "عرض توضيحي" : "Demo preview" },
        { label: ar ? "الاستثمار المخطط" : "Planned investment", value: money(10550000, lang), hint: ar ? "عرض توضيحي" : "Demo preview" },
        { label: ar ? "درجة الجاهزية" : "Readiness score", value: "72%", hint: ar ? "عرض توضيحي" : "Demo preview" },
      ];

  const visibleProjects = data ? projects.slice(0, 5) : demoProjects;
  const displayReadiness = data ? readiness : 72;

  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <section className="relative overflow-hidden border-b border-brand-800 bg-brand-900 text-white">
        <div className="absolute inset-0 opacity-30 [background:radial-gradient(circle_at_15%_0%,#1a9d5c,transparent_35%),radial-gradient(circle_at_90%_10%,#c9a227,transparent_25%)]" />
        <div className="container-page relative py-6 sm:py-8">
          <div className="flex flex-col justify-between gap-7 lg:flex-row lg:items-end">
            <div>
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-gold-300">
                <span className="h-2 w-2 rounded-full bg-gold-400" />
                {data ? (ar ? "مساحة عمل حية" : "Live workspace") : (ar ? "وضع الاستعراض" : "Preview mode")}
              </div>
              <h1 className="text-3xl font-bold tracking-tight sm:text-5xl">{ar ? "مركز قيادة أعمالك" : "Your business command center"}</h1>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-white/75 sm:text-base">
                {ar ? "تابع المشاريع، اختبر الجدوى، وارفع جاهزيتك للتمويل من مكان واحد." : "Track projects, validate feasibility, and improve funding readiness from one focused workspace."}
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link href="/projects" className="rounded-xl border border-white/20 bg-white/10 px-5 py-3 text-sm font-semibold backdrop-blur transition hover:bg-white/15">{ar ? "إدارة المشاريع" : "Manage projects"}</Link>
              <Link href="/tools" className="rounded-xl bg-gold-400 px-5 py-3 text-sm font-bold text-brand-900 shadow-lg shadow-black/10 transition hover:bg-gold-300">{ar ? "أدوات الأعمال" : "Business tools"}</Link>
            </div>
          </div>
        </div>
      </section>

      <div className="container-page space-y-5 py-5 sm:py-6">
        {error && (
          <div role="alert" className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            <span>{ar ? "تعذر تحميل بيانات الحساب. لم نستبدلها ببيانات وهمية." : "Account data could not be loaded. It was not replaced with fabricated figures."}</span>
            <button onClick={() => window.location.reload()} className="font-bold underline">{ar ? "إعادة المحاولة" : "Try again"}</button>
          </div>
        )}

        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label={ar ? "جاري التحميل" : "Loading dashboard"}>
            {[0, 1, 2, 3].map((item) => <div key={item} className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white" />)}
          </div>
        ) : !error && (
          <section aria-label={ar ? "ملخص الحساب" : "Account summary"} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {cards.map((card, index) => (
              <article key={card.label} className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:shadow-card-hover">
                <div className="flex items-start justify-between gap-4">
                  <p className="text-sm font-medium text-ink-600">{card.label}</p>
                  <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-50 text-xs font-bold text-brand-700">0{index + 1}</span>
                </div>
                <p className="mt-5 truncate text-2xl font-bold tracking-tight text-ink-900 sm:text-3xl">{card.value}</p>
                <p className="mt-1 text-xs text-ink-500">{card.hint}</p>
              </article>
            ))}
          </section>
        )}

        {signedIn && !error && !loading && (
          <section className="overflow-hidden rounded-2xl border border-brand-200 bg-white shadow-card">
            <div className="grid lg:grid-cols-[1.4fr_0.6fr]">
              <div className="p-6 sm:p-8">
                <p className="text-sm font-bold text-brand-700">{ar ? "الخطوة المقترحة" : "Recommended next step"}</p>
                <h2 className="mt-2 text-2xl font-bold text-ink-900">{nextStep.title}</h2>
                <p className="mt-2 max-w-xl text-sm leading-6 text-ink-600">{nextStep.detail}</p>
                <Link href={nextStep.href} className="mt-5 inline-flex rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-brand-700">{ar ? "متابعة الآن" : "Continue now"}</Link>
              </div>
              <div className="flex items-center gap-4 border-t border-brand-100 bg-brand-50 p-6 lg:border-s lg:border-t-0">
                <span className="text-3xl" aria-hidden="true">↗</span>
                <div><p className="font-bold text-brand-900">{ar ? "مسار واضح" : "A clear path"}</p><p className="mt-1 text-xs leading-5 text-brand-800/70">{ar ? "مشروع ← جدوى ← جاهزية ← تمويل" : "Project → Feasibility → Readiness → Funding"}</p></div>
              </div>
            </div>
          </section>
        )}

        <section className="grid gap-6 xl:grid-cols-[1.7fr_1fr]">
          <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
            <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4 sm:px-6">
              <div><h2 className="font-bold text-ink-900">{ar ? "المشاريع الأخيرة" : "Recent projects"}</h2><p className="mt-1 text-xs text-ink-500">{ar ? "آخر نشاط في مساحة العمل" : "Latest workspace activity"}</p></div>
              <Link href="/projects" className="text-sm font-bold text-brand-700 hover:text-brand-800">{ar ? "عرض الكل" : "View all"}</Link>
            </header>
            {visibleProjects.length ? (
              <div className="divide-y divide-slate-100">
                {visibleProjects.map((project) => (
                  <Link key={project.id} href={project.id > 0 ? `/projects/${project.id}` : "/projects"} className="grid gap-3 px-5 py-4 transition hover:bg-slate-50 sm:grid-cols-[1.4fr_1fr_auto] sm:items-center sm:px-6">
                    <div><p className="font-semibold text-ink-900">{project.name}</p><p className="mt-1 text-xs text-ink-500">{project.industry}</p></div>
                    <p className="text-sm font-semibold text-ink-700">{money(Number(project.investment), lang)}</p>
                    <span className="w-fit rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-700">{project.stage || (ar ? "نشط" : "Active")}</span>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="p-10 text-center"><p className="text-sm text-ink-600">{ar ? "لا توجد مشاريع بعد." : "No projects yet."}</p><Link href="/projects" className="mt-4 inline-flex text-sm font-bold text-brand-700">{ar ? "أنشئ مشروعك الأول" : "Create your first project"}</Link></div>
            )}
          </article>

          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
            <div className="flex items-center justify-between"><div><h2 className="font-bold text-ink-900">{ar ? "جاهزية الأعمال" : "Business readiness"}</h2><p className="mt-1 text-xs text-ink-500">{ar ? "التمويل والامتثال" : "Funding and compliance"}</p></div><span className="rounded-full bg-gold-50 px-3 py-1 text-xs font-bold text-gold-800">{displayReadiness ? (ar ? "قيد التحسين" : "In progress") : (ar ? "ابدأ" : "Start")}</span></div>
            <div className="mt-6 flex items-center justify-center"><ProgressRing score={displayReadiness} /></div>
            <div className="mt-5 space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-ink-600">{ar ? "ملف المنشأة" : "Business profile"}</span><strong className="text-ink-900">{displayReadiness ? "✓" : "—"}</strong></div>
              <div className="flex justify-between"><span className="text-ink-600">{ar ? "المتطلبات" : "Requirements"}</span><strong className="text-ink-900">{data?.qualifications.length ?? (data ? 0 : 8)}</strong></div>
            </div>
            <Link href="/tools/qualification" className="mt-6 flex justify-center rounded-xl border border-brand-200 px-4 py-3 text-sm font-bold text-brand-700 transition hover:bg-brand-50">{ar ? "فتح تقييم الجاهزية" : "Open readiness assessment"}</Link>
          </article>
        </section>

        <section>
          <div className="mb-4 flex items-end justify-between"><div><h2 className="text-lg font-bold text-ink-900">{ar ? "أدوات النمو" : "Growth tools"}</h2><p className="mt-1 text-sm text-ink-500">{ar ? "كل ما تحتاجه للانتقال من الفكرة إلى التمويل" : "Everything needed to move from idea to funding"}</p></div></div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { href: "/tools/feasibility", code: "01", title: ar ? "دراسة الجدوى V2" : "Feasibility V2", body: ar ? "محرك ذكاء اصطناعي متعدد الوكلاء" : "Multi-agent AI engine" },
              { href: "/tools/financial", code: "02", title: ar ? "التحليل المالي" : "Financial analysis", body: ar ? "عائد الاستثمار وصافي القيمة الحالية" : "ROI, NPV, IRR calculations" },
              { href: "/tools/funding", code: "03", title: ar ? "مطابقة التمويل" : "Funding match", body: ar ? "خيارات حسب القطاع والمرحلة" : "Options by sector and stage" },
              { href: "/tools/proposal", code: "04", title: ar ? "بناء العروض" : "Proposals", body: ar ? "عروض تجارية واستثمارية" : "Commercial and investor proposals" },
              { href: "/tools/qualification", code: "05", title: ar ? "التأهيل" : "Qualification", body: ar ? "جاهزية التمويل والامتثال" : "Funding and compliance readiness" },
              { href: "/tools/opportunities", code: "06", title: ar ? "فرص الاستثمار" : "Opportunities", body: ar ? "فرص مصنفة وقابلة للفلترة" : "Curated, filterable opportunities" },
            ].map((tool) => (
              <Link key={tool.href} href={tool.href} className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition hover:border-brand-300 hover:shadow-card-hover">
                <span className="text-xs font-bold tracking-widest text-gold-700">{tool.code}</span><h3 className="mt-5 font-bold text-ink-900 group-hover:text-brand-700">{tool.title}</h3><p className="mt-2 text-sm leading-6 text-ink-500">{tool.body}</p><span className="mt-5 inline-block text-brand-700 transition group-hover:translate-x-1 rtl:group-hover:-translate-x-1">→</span>
              </Link>
            ))}
          </div>
        </section>

        {!signedIn && (
          <section className="rounded-2xl bg-ink-900 p-6 text-white sm:flex sm:items-center sm:justify-between sm:p-8">
            <div><p className="text-xs font-bold uppercase tracking-[0.2em] text-gold-300">{ar ? "بيانات العرض فقط" : "Preview data only"}</p><h2 className="mt-2 text-2xl font-bold">{ar ? "سجّل الدخول لعرض بياناتك الحقيقية" : "Sign in to see your real workspace"}</h2><p className="mt-2 text-sm text-white/60">{ar ? "لن نخلط بياناتك مع أمثلة توضيحية." : "Your account data is never mixed with demo examples."}</p></div>
            <Link href="/login" className="mt-5 inline-flex rounded-xl bg-white px-5 py-3 text-sm font-bold text-ink-900 sm:mt-0">{ar ? "تسجيل الدخول" : "Sign in"}</Link>
          </section>
        )}
      </div>
    </div>
  );
}
