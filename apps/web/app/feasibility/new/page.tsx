"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import {
  computeStudy,
  createStudy,
  getProject,
  getToken,
  listStudies,
  matchFunding,
  reportDownloadUrl,
  saveStudyStep,
  type FundingMatch,
  type Study,
} from "@/lib/api";

const INDUSTRIES = ["technology", "healthcare", "retail", "industrial", "tourism", "education"] as const;
const STAGES = ["idea", "mvp", "early_revenue", "growth"] as const;

const copy = {
  ar: {
    title: "دراسة جدوى جديدة",
    subtitle: "أدخل بيانات مشروعك واحصل على تحليل مالي فوري ومطابقة تمويل.",
    loginRequired: "يلزم تسجيل الدخول لإنشاء دراسة جدوى.",
    goLogin: "تسجيل الدخول",
    demoNote: "بيئة تجريبية: يتطلب هذا الإجراء تشغيل الواجهة البرمجية وضبط NEXT_PUBLIC_API_BASE_URL وقاعدة بيانات حقيقية.",
    step1: {
      heading: "١. بيانات المشروع",
      name: "اسم المشروع",
      industry: "القطاع",
      investment: "الاستثمار الأولي (ر.س)",
      stage: "المرحلة",
      next: "التالي",
      creating: "جارٍ الإنشاء...",
    },
    step2: {
      heading: "٢. التدفقات النقدية",
      revenue: "الإيرادات السنوية (سنوات ١-٥، مفصولة بفواصل)",
      costs: "التكاليف التشغيلية السنوية (سنوات ١-٥، مفصولة بفواصل)",
      fixedCosts: "التكاليف الثابتة السنوية (ر.س)",
      variableCost: "نسبة التكلفة المتغيرة من الإيراد (%)",
      discount: "معدل الخصم (%)",
      compute: "احسب النتائج",
      computing: "جارٍ الحساب...",
      assumptionNote: "كل القيم هنا افتراض مستخدم (USER_ASSUMPTION) وليست حقائق سوقية.",
      back: "العودة للمدخلات",
    },
    step3: {
      heading: "٣. النتائج",
      verdict: { feasible: "قابل للتنفيذ", borderline: "حدّي", not_feasible: "غير قابل للتنفيذ" },
      npv: "صافي القيمة الحالية",
      irr: "معدل العائد الداخلي",
      payback: "فترة الاسترداد",
      roi: "العائد على الاستثمار",
      funding: "أفضل مطابقات التمويل",
      report: "تنزيل التقرير",
      newStudy: "دراسة جديدة",
    },
    industryLabels: { technology: "تقنية", healthcare: "صحة", retail: "تجزئة", industrial: "صناعة", tourism: "سياحة", education: "تعليم" } as Record<string, string>,
    stageLabels: { idea: "فكرة", mvp: "نموذج أولي", early_revenue: "إيرادات مبكرة", growth: "نمو" } as Record<string, string>,
  },
  en: {
    title: "New Feasibility Study",
    subtitle: "Enter your project details and get an instant financial analysis and funding match.",
    loginRequired: "You need to sign in to create a feasibility study.",
    goLogin: "Sign in",
    demoNote: "Demo environment: this action requires the API running, NEXT_PUBLIC_API_BASE_URL set, and a real database.",
    step1: {
      heading: "1. Project details",
      name: "Project name",
      industry: "Industry",
      investment: "Initial investment (SAR)",
      stage: "Stage",
      next: "Next",
      creating: "Creating...",
    },
    step2: {
      heading: "2. Cash flow assumptions",
      revenue: "Annual revenue, years 1-5 (comma-separated)",
      costs: "Annual operating costs, years 1-5 (comma-separated)",
      fixedCosts: "Annual fixed costs (SAR)",
      variableCost: "Variable cost as % of revenue",
      discount: "Discount rate (%)",
      compute: "Compute results",
      computing: "Computing...",
      assumptionNote: "Every value here is a USER_ASSUMPTION, not a verified market fact.",
      back: "Back to inputs",
    },
    step3: {
      heading: "3. Results",
      verdict: { feasible: "Feasible", borderline: "Borderline", not_feasible: "Not feasible" },
      npv: "NPV",
      irr: "IRR",
      payback: "Payback",
      roi: "ROI",
      funding: "Top funding matches",
      report: "Download report",
      newStudy: "New study",
    },
    industryLabels: { technology: "Technology", healthcare: "Healthcare", retail: "Retail", industrial: "Industrial", tourism: "Tourism", education: "Education" } as Record<string, string>,
    stageLabels: { idea: "Idea", mvp: "MVP", early_revenue: "Early revenue", growth: "Growth" } as Record<string, string>,
  },
};

function fmtSAR(n: number | null | undefined, locale: "ar" | "en") {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-SA", {
    style: "currency",
    currency: "SAR",
    maximumFractionDigits: 0,
  }).format(n);
}

function fmtMetric(n: number | null | undefined, locale: "ar" | "en", digits = 1) {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-US", {
    maximumFractionDigits: digits,
  }).format(n);
}

export default function NewFeasibilityStudyPage() {
  const { locale } = useLanguage();
  const router = useRouter();
  const c = copy[locale];

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [industry, setIndustry] = useState<string>("technology");
  const [investment, setInvestment] = useState<number>(500000);
  const [stage, setStage] = useState<string>("mvp");

  const [revenues, setRevenues] = useState("");
  const [operatingCosts, setOperatingCosts] = useState("");
  const [fixedCosts, setFixedCosts] = useState<number | "">("");
  const [variableCostPercent, setVariableCostPercent] = useState<number | "">("");
  const [discount, setDiscount] = useState<number>(10);

  const [study, setStudy] = useState<Study | null>(null);
  const [funding, setFunding] = useState<FundingMatch[] | null>(null);
  const [linkedProjectId, setLinkedProjectId] = useState<number | undefined>();

  const token = getToken();

  useEffect(() => {
    if (!token) return;
    const rawId = new URLSearchParams(window.location.search).get("project_id");
    const projectId = rawId ? Number(rawId) : NaN;
    if (!Number.isInteger(projectId) || projectId <= 0) return;
    void getProject(token, projectId)
      .then(async (project) => {
        setLinkedProjectId(project.id);
        setName(project.name);
        setIndustry(project.industry);
        setInvestment(project.investment);
        setStage(project.stage);
        const existing = (await listStudies(token, project.id))[0];
        if (existing) {
          router.replace(`/projects/${project.id}/studies/${existing.id}`);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [router, token]);

  async function onCreateStudy(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const created = await createStudy(token, { title: name, industry, investment, project_id: linkedProjectId, study_type: "general" });
      if (linkedProjectId) {
        router.replace(`/projects/${created.project_id}/studies/${created.id}`);
        return;
      }
      setStudy(created);
      setStep(2);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onCompute(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !study) return;
    setBusy(true);
    setError(null);
    try {
      const revenueValues = revenues.split(",").map((value) => Number(value.trim()));
      const costValues = operatingCosts.split(",").map((value) => Number(value.trim()));
      if (revenueValues.length !== 5 || costValues.length !== 5 || [...revenueValues, ...costValues].some((value) => !Number.isFinite(value) || value < 0)) {
        throw new Error(locale === "ar" ? "أدخل خمس قيم صحيحة للإيرادات والتكاليف." : "Enter five valid revenue and cost values.");
      }
      const annual_cash_flows = revenueValues.map((revenue, index) => revenue - costValues[index]);
      const discount_rate = discount / 100;
      const fixed = Number(fixedCosts);
      const variable = Number(variableCostPercent);
      if (!Number.isFinite(fixed) || fixed < 0 || !Number.isFinite(variable) || variable < 0) {
        throw new Error(locale === "ar" ? "أدخل تكاليف ثابتة ونسبة متغيرة كافتراض مستخدم، أو اترك الحساب بعد تعبئتهما." : "Enter user-assumed fixed costs and variable percent before computing.");
      }
      await saveStudyStep(token, study.id, 2, { revenues: revenueValues, operating_costs: costValues, annual_cash_flows, discount_rate, fixed_costs: fixed, variable_cost_percent: variable, source: "USER_ASSUMPTION" });
      const computed = await computeStudy(token, study.id, { annual_cash_flows, discount_rate });
      setStudy(computed);
      const matches = await matchFunding({ industry, stage, has_mvp: stage !== "idea", has_technical_team: true });
      setFunding(matches);
      setStep(3);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onDownloadReport(fmt: "pdf" | "docx") {
    if (!token || !study) return;
    setError(null);
    try {
      const res = await fetch(reportDownloadUrl(study.id, fmt, locale), {
        headers: { Authorization: "Bearer " + token },
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || res.statusText);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "feasibility_" + study.id + "_" + locale + "." + fmt;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  if (!token) {
    return (
      <main className="container-page py-16">
        <div className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <h1 className="text-xl font-semibold text-ink-900">{c.title}</h1>
          <p className="mt-4 text-sm text-ink-700">{c.loginRequired}</p>
          <Link
            href="/login"
            className="mt-6 inline-flex rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700"
          >
            {c.goLogin}
          </Link>
          <p className="mt-6 text-xs text-ink-500">{c.demoNote}</p>
        </div>
      </main>
    );
  }

  const result = study?.result;
  const verdict = result?.verdict as keyof typeof c.step3.verdict | undefined;
  const contributionMargin = 1 - Number(variableCostPercent || 0) / 100;
  const breakEvenRevenue = contributionMargin > 0 && Number(fixedCosts) > 0 ? Number(fixedCosts) / contributionMargin : null;

  return (
    <main className="container-page py-14">
      <h1 className="text-3xl font-semibold text-ink-900">{c.title}</h1>
      <p className="mt-2 max-w-2xl text-ink-700">{c.subtitle}</p>

      <ol className="mt-8 flex gap-3 text-sm">
        {[1, 2, 3].map((n) => (
          <li
            key={n}
            className={
              "flex h-8 w-8 items-center justify-center rounded-full font-medium " +
              (step === n ? "bg-brand-600 text-white" : step > n ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-ink-500")
            }
          >
            {n}
          </li>
        ))}
      </ol>

      {error && <p className="mt-6 max-w-2xl rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {step === 1 && (
        <form onSubmit={onCreateStudy} className="mt-8 max-w-md space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-ink-900">{c.step1.heading}</h2>
          <label className="block text-sm">
            <span className="text-ink-700">{c.step1.name}</span>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
            />
          </label>
          <label className="block text-sm">
            <span className="text-ink-700">{c.step1.industry}</span>
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 outline-none focus:border-brand-500"
            >
              {INDUSTRIES.map((i) => (
                <option key={i} value={i}>
                  {c.industryLabels[i]}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="text-ink-700">{c.step1.investment}</span>
            <input
              type="number"
              required
              min={1}
              value={investment}
              onChange={(e) => setInvestment(parseFloat(e.target.value))}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
            />
          </label>
          <label className="block text-sm">
            <span className="text-ink-700">{c.step1.stage}</span>
            <select
              value={stage}
              onChange={(e) => setStage(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 outline-none focus:border-brand-500"
            >
              {STAGES.map((s) => (
                <option key={s} value={s}>
                  {c.stageLabels[s]}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {busy ? c.step1.creating : c.step1.next}
          </button>
        </form>
      )}

      {step === 2 && (
        <form onSubmit={onCompute} className="mt-8 max-w-md space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="font-semibold text-ink-900">{c.step2.heading}</h2>
          <p className="text-xs text-amber-800 rounded-lg bg-amber-50 p-2">{c.step2.assumptionNote}</p>
          <label className="block text-sm">
            <span className="text-ink-700">{c.step2.revenue}</span>
            <input
              type="text"
              required
              value={revenues}
              onChange={(e) => setRevenues(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
            />
          </label>
          <label className="block text-sm">
            <span className="text-ink-700">{c.step2.costs}</span>
            <input type="text" required value={operatingCosts} onChange={(e) => setOperatingCosts(e.target.value)} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500" />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm">
              <span className="text-ink-700">{c.step2.fixedCosts}</span>
              <input type="number" min={0} required value={fixedCosts} onChange={(e) => setFixedCosts(e.target.value === "" ? "" : Number(e.target.value))} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500" />
            </label>
            <label className="block text-sm">
              <span className="text-ink-700">{c.step2.variableCost}</span>
              <input type="number" min={0} max={99} required value={variableCostPercent} onChange={(e) => setVariableCostPercent(e.target.value === "" ? "" : Number(e.target.value))} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500" />
            </label>
          </div>
          <label className="block text-sm">
            <span className="text-ink-700">{c.step2.discount}</span>
            <input
              type="number"
              required
              min={0}
              max={100}
              step={0.5}
              value={discount}
              onChange={(e) => setDiscount(parseFloat(e.target.value))}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-brand-500"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-md bg-brand-600 px-4 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {busy ? c.step2.computing : c.step2.compute}
          </button>
        </form>
      )}

      {step === 3 && result && (
        <div className="mt-8 max-w-2xl space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="font-semibold text-ink-900">{c.step3.heading}</h2>
            {verdict && (
              <span
                className={
                  "mt-3 inline-flex rounded-full px-3 py-1 text-sm font-semibold " +
                  (verdict === "feasible"
                    ? "bg-emerald-50 text-emerald-700"
                    : verdict === "borderline"
                    ? "bg-amber-50 text-amber-700"
                    : "bg-red-50 text-red-700")
                }
              >
                {c.step3.verdict[verdict] ?? verdict}
              </span>
            )}
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p className="text-xs text-ink-500">{c.step3.npv}</p>
                <p className="mt-1 text-sm font-semibold">{fmtSAR(result.npv, locale)}</p>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p className="text-xs text-ink-500">{c.step3.irr}</p>
                <p className="mt-1 text-sm font-semibold">{fmtMetric(result.irr_percent, locale)}%</p>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p className="text-xs text-ink-500">{c.step3.payback}</p>
                <p className="mt-1 text-sm font-semibold">{fmtMetric(result.payback_years, locale)} {locale === "ar" ? "سنة" : "years"}</p>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p className="text-xs text-ink-500">{c.step3.roi}</p>
                <p className="mt-1 text-sm font-semibold">{fmtMetric(result.roi_percent, locale)}%</p>
              </div>
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p className="text-xs text-ink-500">{locale === "ar" ? "إيراد التعادل" : "Break-even revenue"}</p>
                <p className="mt-1 text-sm font-semibold">{fmtSAR(breakEvenRevenue, locale)}</p>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                onClick={() => onDownloadReport("pdf")}
                className="rounded-md border border-brand-500 px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
              >
                {c.step3.report} (PDF)
              </button>
              <button
                onClick={() => onDownloadReport("docx")}
                className="rounded-md border border-brand-500 px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50"
              >
                {c.step3.report} (DOCX)
              </button>
              <button
                type="button"
                onClick={() => setStep(2)}
                data-testid="back-to-inputs"
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-ink-700 hover:border-brand-500"
              >
                {c.step2.back}
              </button>
              {study ? (
                <Link
                  href={`/projects/${study.project_id}/studies/${study.id}`}
                  data-testid="open-study-workspace-from-results"
                  className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white"
                >
                  {locale === "ar" ? "فتح مساحة الدراسة" : "Open study workspace"}
                </Link>
              ) : null}
              <Link
                href="/projects"
                className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-ink-700 hover:border-brand-500"
              >
                {c.step3.newStudy}
              </Link>
            </div>
          </div>

          {result.sensitivity?.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="font-semibold text-ink-900">{locale === "ar" ? "تحليل الحساسية" : "Sensitivity analysis"}</h3>
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b text-start text-ink-500"><th className="p-2">{locale === "ar" ? "تغير الإيراد" : "Revenue change"}</th><th className="p-2">NPV</th><th className="p-2">IRR</th><th className="p-2">{locale === "ar" ? "القرار" : "Verdict"}</th></tr></thead>
                  <tbody>{result.sensitivity.map((row) => <tr key={row.revenue_change_percent} className="border-b border-slate-100"><td className="p-2">{fmtMetric(row.revenue_change_percent, locale)}%</td><td className="p-2">{fmtSAR(row.npv, locale)}</td><td className="p-2">{fmtMetric(row.irr_percent, locale)}%</td><td className="p-2">{c.step3.verdict[row.verdict as keyof typeof c.step3.verdict] || row.verdict}</td></tr>)}</tbody>
                </table>
              </div>
            </div>
          )}

          {funding && funding.length > 0 && (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-ink-500">{c.step3.funding}</h3>
              <div className="mt-4 space-y-3">
                {funding.slice(0, 3).map((f) => (
                  <div key={f.program} className="flex items-center gap-3 text-sm">
                    <span className="w-24 shrink-0 font-mono text-ink-700">{f.program}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-gradient-to-r from-brand-500 to-gold-500" style={{ width: f.score_percent + "%" }} />
                    </div>
                    <span className="w-12 text-end font-mono text-ink-700">{f.score_percent}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
