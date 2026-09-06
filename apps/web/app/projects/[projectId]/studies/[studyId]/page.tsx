"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getProject, getStudy, getToken, saveStudyStep, type Project, type Study, type StudySaveState } from "@/lib/api";
import { useLanguage } from "@/components/LanguageProvider";
import EvidenceTab from "@/components/study/EvidenceTab";
import AssumptionsTab from "@/components/study/AssumptionsTab";
import BusinessProfileTab from "@/components/study/BusinessProfileTab";
import FundingTab from "@/components/study/FundingTab";
import ValidationTab from "@/components/study/ValidationTab";
import LaunchTab from "@/components/study/LaunchTab";
import GrowthTab from "@/components/study/GrowthTab";
import FinancialAnalysisTab from "@/components/study/FinancialAnalysisTab";

const sections = [
  "overview",
  "profile",
  "advisor",
  "evidence",
  "assumptions",
  "financial",
  "scenarios",
  "risks",
  "funding",
  "validation",
  "launch",
  "growth",
  "compliance",
  "report",
  "sources",
  "versions",
] as const;

const labels = {
  ar: [
    "نظرة عامة",
    "ملف المشروع",
    "المستشار",
    "أدلة السوق",
    "الافتراضات",
    "التحليل المالي",
    "السيناريوهات",
    "المخاطر",
    "التمويل",
    "التحقق الميداني والافتراضات",
    "تنفيذ الإطلاق والأداء الفعلي",
    "نمو وتوسع الأعمال (Growth OS)",
    "الامتثال والتراخيص",
    "التقرير",
    "المصادر",
    "سجل الإصدارات",
  ],
  en: [
    "Overview",
    "Business profile",
    "Advisor",
    "Market evidence",
    "Assumptions",
    "Financial analysis",
    "Scenarios",
    "Risks",
    "Funding",
    "Market Validation",
    "Launch & Actuals",
    "Growth OS",
    "Compliance & licensing",
    "Report",
    "Sources",
    "Version history",
  ],
};

export default function StudyWorkspacePage({ params }: { params: Promise<{ projectId: string; studyId: string }> }) {
  const route = use(params);
  const projectId = Number(route.projectId);
  const studyId = Number(route.studyId);
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const [project, setProject] = useState<Project | null>(null);
  const [study, setStudy] = useState<Study | null>(null);
  const [active, setActive] = useState<(typeof sections)[number]>("overview");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [notes, setNotes] = useState("");
  const [saveState, setSaveState] = useState<StudySaveState>("idle");
  const hydrated = useRef(false);
  const revisionRef = useRef<number | undefined>(undefined);
  const token = getToken();
  const persistedStudyId = study?.id;
  const currentStep = study?.current_step;

  const reload = useCallback(async () => {
    if (!token) return;
    const [projectRow, studyRow] = await Promise.all([getProject(token, projectId), getStudy(token, studyId)]);
    if (studyRow.project_id !== projectRow.id) {
      throw new Error(ar ? "الدراسة لا تنتمي إلى هذا المشروع." : "Study does not belong to this project.");
    }
    setProject(projectRow);
    setStudy(studyRow);
    revisionRef.current = studyRow.revision;
    const saved = studyRow.payload[`step_${studyRow.current_step}`];
    setNotes(saved && typeof saved === "object" && "notes" in saved ? String((saved as { notes?: unknown }).notes ?? "") : "");
    hydrated.current = true;
  }, [ar, projectId, studyId, token]);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    reload()
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)))
      .finally(() => setLoading(false));
  }, [reload, token]);

  useEffect(() => {
    const applyHash = () => {
      const hash = window.location.hash.replace("#", "") as (typeof sections)[number];
      if ((sections as readonly string[]).includes(hash)) setActive(hash);
    };
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, []);

  useEffect(() => {
    if (!token || !persistedStudyId || !currentStep || !revisionRef.current || !hydrated.current) return;
    setSaveState("saving");
    const timer = window.setTimeout(() => {
      saveStudyStep(token, persistedStudyId, currentStep, { notes }, revisionRef.current)
        .then((saved) => {
          revisionRef.current = saved.revision;
          setStudy(saved);
          setSaveState("saved");
        })
        .catch((reason) => {
          setError(reason instanceof Error ? reason.message : String(reason));
          setSaveState("error");
        });
    }, 700);
    return () => window.clearTimeout(timer);
  }, [currentStep, notes, persistedStudyId, token]);

  const stateLabel = useMemo(
    () => ({ idle: "", saving: ar ? "جارٍ الحفظ..." : "Saving...", saved: ar ? "تم الحفظ" : "Saved", error: ar ? "تعذر الحفظ" : "Save failed" })[saveState],
    [ar, saveState]
  );

  // Keep server HTML and the first browser render identical while session state loads.
  if (loading) {
    return <main className="container-page py-16">{ar ? "جارٍ استعادة الدراسة المحفوظة..." : "Restoring saved study..."}</main>;
  }

  if (!token) {
    return (
      <main className="container-page py-16">
        <p>{ar ? "انتهت الجلسة أو لم تسجّل الدخول." : "Your session expired or you are not signed in."}</p>
        <Link href={`/login?next=${encodeURIComponent(`/projects/${projectId}/studies/${studyId}`)}`} className="mt-4 inline-flex rounded-lg bg-brand-600 px-4 py-2 text-white">
          {ar ? "تسجيل الدخول والعودة للدراسة" : "Sign in and return to study"}
        </Link>
      </main>
    );
  }

  if (error && !study) {
    return (
      <main className="container-page py-16">
        <p role="alert" className="rounded-lg bg-red-50 p-4 text-red-700">
          {error}
        </p>
      </main>
    );
  }

  if (!study || !project) return null;

  // Opportunity lineage from study payload
  const lineage = (study.payload?.opportunity_lineage || null) as {
    source_opportunity_id?: number;
    source_opportunity_title_ar?: string;
    source_opportunity_title_en?: string;
    opportunity_type?: string;
    brand_name?: string | null;
    sector?: string;
    source_owner?: string;
    official_source_url?: string;
    verification_status?: string;
    data_version?: string;
    transferred_at?: string;
    budget_type?: string;
    is_user_assumption?: boolean;
    budget_amount?: number;
    budget_notes?: string | null;
    transferred_facts?: Record<string, unknown>;
  } | null;

  return (
    <main className="container-page py-8" data-testid="study-workspace">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href={`/projects/${project.id}`} className="text-sm text-brand-700 hover:underline">
            {project.name}
          </Link>
          <h1 className="mt-1 text-2xl font-bold">{study.title}</h1>
          <p className="mt-1 text-sm text-ink-500">
            {ar ? `الخطوة المحفوظة ${study.current_step}` : `Saved step ${study.current_step}`} · {study.status}
          </p>
        </div>
        <span aria-live="polite" className={`rounded-full px-3 py-1 text-sm ${saveState === "error" ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700"}`}>
          {stateLabel}
        </span>
      </div>

      {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <div className="mt-7 grid gap-6 lg:grid-cols-[240px_1fr]">
        <nav aria-label={ar ? "أقسام الدراسة" : "Study sections"} className="rounded-2xl border border-slate-200 bg-white p-3">
          {sections.map((section, index) => (
            <button
              key={section}
              data-testid={`study-section-${section}`}
              onClick={() => {
                setActive(section);
                window.location.hash = section;
              }}
              className={`block w-full rounded-lg px-3 py-2 text-start text-sm ${active === section ? "bg-brand-50 font-semibold text-brand-800" : "hover:bg-slate-50"}`}
            >
              {labels[locale][index]}
            </button>
          ))}
        </nav>

        <section className="min-h-[420px] rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold">{labels[locale][sections.indexOf(active)]}</h2>

          {active === "overview" ? (
            <div className="mt-5 space-y-6">
              {/* SOURCED OPPORTUNITY PROVENANCE & LINEAGE BANNER */}
              {lineage && (
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50/70 p-5 shadow-sm" data-testid="opportunity-lineage-banner">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="rounded-full bg-emerald-200/80 px-3 py-1 text-xs font-semibold text-emerald-900">
                      {ar ? "أصل الدراسة: فرصة استثمارية معتمدة وموثقة" : "Lineage: Sourced from Verified Opportunity"}
                    </span>
                    <span className="rounded-full bg-white/80 px-2.5 py-0.5 text-xs font-medium text-emerald-800">
                      {lineage.verification_status || "VERIFIED_CURRENT"} · v{lineage.data_version || "1.0.0"}
                    </span>
                  </div>
                  <h3 className="mt-2 text-lg font-bold text-emerald-950">
                    {ar ? lineage.source_opportunity_title_ar : lineage.source_opportunity_title_en}
                  </h3>
                  {lineage.brand_name && (
                    <p className="text-xs font-semibold text-emerald-800">{lineage.brand_name}</p>
                  )}
                  <p className="mt-1 text-xs text-emerald-800">
                    {ar ? "جهة المصدر الرسمي:" : "Official Source Owner:"} <strong>{lineage.source_owner}</strong>
                    {lineage.official_source_url && (
                      <>
                        {" · "}
                        <a
                          href={lineage.official_source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="underline hover:text-emerald-950"
                        >
                          {ar ? "رابط الوثيقة الرسمية ↗" : "Official Portal ↗"}
                        </a>
                      </>
                    )}
                  </p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-4 text-xs">
                    <div className="rounded-xl bg-white/80 p-3">
                      <span className="text-slate-500">{ar ? "القطاع المنقول:" : "Transferred Sector:"}</span>
                      <p className="mt-1 font-semibold text-slate-800">{lineage.sector}</p>
                    </div>
                    <div className="rounded-xl bg-white/80 p-3">
                      <span className="text-slate-500">{ar ? "نوع الفرصة:" : "Opportunity Type:"}</span>
                      <p className="mt-1 font-semibold text-slate-800">
                        {lineage.opportunity_type === "FRANCHISE" ? (ar ? "امتياز تجاري" : "Franchise") : (ar ? "فرصة استثمارية" : "Business Opp")}
                      </p>
                    </div>
                    <div className="rounded-xl bg-white/80 p-3">
                      <span className="text-slate-500">{ar ? "طبيعة الميزانية:" : "Budget Source:"}</span>
                      <p className="mt-1 font-semibold text-slate-800">
                        {lineage.budget_type === "USER_ASSUMPTION"
                          ? (ar ? "افتراض مستخدم (USER_ASSUMPTION)" : "User Assumption")
                          : (ar ? "حد أدنى رسمي" : "Published Minimum")}
                      </p>
                    </div>
                    <div className="rounded-xl bg-white/80 p-3">
                      <span className="text-slate-500">{ar ? "تاريخ التوثيق:" : "Transferred At:"}</span>
                      <p className="mt-1 font-mono text-slate-800">{lineage.transferred_at?.slice(0, 10) || "2026-09-04"}</p>
                    </div>
                  </div>
                </div>
              )}

              <div className="grid gap-4 sm:grid-cols-3">
                <article className="rounded-xl bg-slate-50 p-4">
                  <p className="text-sm text-ink-500">{ar ? "الحالة" : "Status"}</p>
                  <p className="mt-1 font-semibold">{study.status}</p>
                </article>
                <article className="rounded-xl bg-slate-50 p-4">
                  <p className="text-sm text-ink-500">
                    {ar ? "الميزانية" : "Budget"}
                    {lineage?.budget_type === "USER_ASSUMPTION" && (
                      <span className="mx-1 text-[11px] font-medium text-amber-700">
                        {ar ? "(افتراض مستخدم USER_ASSUMPTION)" : "(User Assumption)"}
                      </span>
                    )}
                  </p>
                  <p className="mt-1 font-semibold">
                    {new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-SA", { style: "currency", currency: "SAR", maximumFractionDigits: 0 }).format(project.investment)}
                  </p>
                </article>
                <article className="rounded-xl bg-slate-50 p-4">
                  <p className="text-sm text-ink-500">{ar ? "آخر خطوة" : "Current step"}</p>
                  <p className="mt-1 font-semibold">{study.current_step}</p>
                </article>
              </div>
            </div>
          ) : active === "profile" ? (
            <BusinessProfileTab token={token} studyId={study.id} locale={locale} />
          ) : active === "evidence" ? (
            <EvidenceTab token={token} studyId={study.id} locale={locale} />
          ) : active === "assumptions" ? (
            <AssumptionsTab token={token} studyId={study.id} locale={locale} />
          ) : active === "financial" ? (
            <FinancialAnalysisTab token={token} study={study} locale={locale} onComputed={reload} onOpenAssumptions={() => { setActive("assumptions"); window.location.hash = "assumptions"; }} />
          ) : active === "funding" ? (
            <FundingTab token={token} studyId={study.id} locale={locale} />
          ) : active === "validation" ? (
            <ValidationTab token={token} studyId={study.id} locale={locale} />
          ) : active === "launch" ? (
            <LaunchTab token={token} studyId={study.id} locale={locale} />
          ) : active === "growth" ? (
            <GrowthTab token={token} studyId={study.id} locale={locale} onNavigateTab={(tab) => setActive(tab as any)} />
          ) : active === "sources" && lineage ? (
            <div className="mt-5 space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <h3 className="font-bold text-slate-900">{ar ? "توثيق مصدر الفرصة المرجعية" : "Opportunity Sourced Provenance"}</h3>
                <div className="mt-3 space-y-2 text-xs text-slate-700">
                  <p><span className="font-medium text-slate-500">{ar ? "الفرصة الأصلية:" : "Original Opportunity:"}</span> {ar ? lineage.source_opportunity_title_ar : lineage.source_opportunity_title_en}</p>
                  <p><span className="font-medium text-slate-500">{ar ? "جهة المصدر الرسمية:" : "Source Authority:"}</span> {lineage.source_owner}</p>
                  <p><span className="font-medium text-slate-500">{ar ? "الرابط الرسمي:" : "Official URL:"}</span> <a href={lineage.official_source_url} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline">{lineage.official_source_url}</a></p>
                  <p><span className="font-medium text-slate-500">{ar ? "حالة التوثيق:" : "Status:"}</span> {lineage.verification_status}</p>
                  <p><span className="font-medium text-slate-500">{ar ? "إصدار البيانات:" : "Data Version:"}</span> {lineage.data_version}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-5">
              <p className="text-sm text-ink-600">
                {ar ? "دوّن مدخلات هذا القسم. تُحفظ التغييرات تلقائياً في الدراسة الدائمة." : "Record this section’s inputs. Changes are autosaved to the permanent study."}
              </p>
              <label className="mt-4 block text-sm">
                <span>{ar ? "ملاحظات القسم" : "Section notes"}</span>
                <textarea
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  rows={10}
                  className="mt-2 w-full rounded-xl border border-slate-300 p-3 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100"
                />
              </label>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
