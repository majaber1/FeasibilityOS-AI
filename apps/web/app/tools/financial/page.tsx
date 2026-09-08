"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { ServiceHeader } from "@/components/ui/ServiceHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { Badge } from "@/components/ui/Badge";
import { evaluateFinancial, evaluateSensitivity, createFinancialAnalysis, getFinancialImportPreview, getToken, listStudies, type FeasibilityEvalResponse, type ImportPreview, type Study } from "@/lib/api";
import { useProjectContext } from "@/lib/use-project-context";
import { ContextBanner } from "@/components/ui/ContextBanner";
import { ImportSource } from "@/components/ui/ContextBanner";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";

function money(value: number) {
  return new Intl.NumberFormat("en-SA", { style: "currency", currency: "SAR", maximumFractionDigits: 0 }).format(value);
}

export default function FinancialAnalysisPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";

  const [investment, setInvestment] = useState("");
  const [cashFlowsStr, setCashFlowsStr] = useState("");
  const [discountRate, setDiscountRate] = useState("10");
  const [result, setResult] = useState<FeasibilityEvalResponse | null>(null);
  const [sensitivity, setSensitivity] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [studies, setStudies] = useState<Study[]>([]);
  const [importPreview, setImportPreview] = useState<ImportPreview | null>(null);
  const { project, error: projectError } = useProjectContext();

  useEffect(() => {
    if (project) setInvestment(String(project.investment));
  }, [project]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    listStudies(token, project?.id).then(setStudies).catch(() => undefined);
  }, [project?.id]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const inv = Number(investment);
    const flows = cashFlowsStr.split(",").map((s) => Number(s.trim())).filter((n) => !isNaN(n));
    const dr = Number(discountRate) / 100;

    if (!inv || flows.length === 0) {
      setError(ar ? "يرجى إدخال قيم صحيحة" : "Please enter valid values");
      return;
    }

    setLoading(true);
    try {
      const r = await evaluateFinancial({ investment: inv, annual_cash_flows: flows, discount_rate: dr });
      setResult(r);
      const s = await evaluateSensitivity({ investment: inv, annual_cash_flows: flows, discount_rate: dr });
      setSensitivity(s);
    } catch {
      setError(ar ? "حدث خطأ في التحليل" : "An error occurred during analysis");
    } finally {
      setLoading(false);
    }
  }

  async function handleImport(studyId: number) {
    const token = getToken();
    if (!token) { setError(ar ? "سجّل الدخول لاستيراد الافتراضات." : "Sign in to import assumptions."); return; }
    setError("");
    try {
      const preview = await getFinancialImportPreview(token, studyId);
      setImportPreview(preview);
      if (preview.investment) setInvestment(String(preview.investment));
      if (preview.annual_cash_flows?.length) setCashFlowsStr(preview.annual_cash_flows.join(", "));
      if (preview.discount_rate) setDiscountRate(String(preview.discount_rate * 100));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleSave() {
    const token = getToken();
    if (!token || !result) { setError(ar ? "حلّل أولاً ثم احفظ." : "Analyze first, then save."); return; }
    const flows = cashFlowsStr.split(",").map((s) => Number(s.trim())).filter((n) => !isNaN(n));
    setSaving(true);
    setError("");
    try {
      await createFinancialAnalysis(token, {
        title: project ? `${ar ? "تحليل" : "Analysis"} — ${project.name}` : (ar ? "تحليل مستقل" : "Standalone analysis"),
        investment: Number(investment),
        annual_cash_flows: flows,
        discount_rate: Number(discountRate) / 100,
        project_id: project?.id,
        feasibility_study_id: importPreview?.study_id,
        import_meta: importPreview ? { source_record: importPreview.source_record, imported_fields: importPreview.imported_fields, last_sync: importPreview.last_sync } : {},
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <ServiceHeader
        icon="💰"
        title={ar ? "التحليل المالي" : "Financial Analysis"}
        subtitle={ar
          ? "حلل العائد على الاستثمار والقيمة الحالية الصافية ومعدل العائد الداخلي بشكل مستقل"
          : "Analyze ROI, NPV, IRR, payback period, and break-even independently"}
        breadcrumb={[{ label: ar ? "الأدوات" : "Tools", href: "/tools" }]}
      />

      <div className="container-page space-y-8 py-8">
        {project && (
          <ContextBanner label={ar ? "التحليل مرتبط بالمشروع:" : "Analysis linked to project:"} name={project.name} href={`/businesses/${project.id}`} />
        )}
        {projectError && <Alert tone="danger">{projectError}</Alert>}
        {studies.length > 0 && (
          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
            <h2 className="font-bold text-ink-900">{ar ? "استيراد افتراضات دراسة الجدوى (اختياري)" : "Import feasibility assumptions (optional)"}</h2>
            <p className="mt-1 text-sm text-ink-600">{ar ? "لن ندمج البيانات تلقائياً. اختر الدراسة ثم راجع الحقول." : "Nothing is merged automatically. Choose a study, then review the fields."}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {studies.map((s) => (
                <button key={s.id} type="button" onClick={() => handleImport(s.id)} className="rounded-lg border border-slate-300 px-3 py-2 text-xs font-semibold hover:border-brand-500">
                  {s.title}
                </button>
              ))}
            </div>
            {importPreview && (
              <div className="mt-4">
                <ImportSource locale={ar ? "ar" : "en"} sourceRecord={importPreview.source_record} fields={importPreview.imported_fields} lastSync={importPreview.last_sync} />
              </div>
            )}
          </section>
        )}
        <div className="grid gap-8 lg:grid-cols-[1fr_1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
            <h2 className="text-xl font-bold text-ink-900">{ar ? "بيانات التحليل" : "Analysis inputs"}</h2>
            <p className="mt-2 text-sm text-ink-600">
              {ar ? "أدخل بيانات الاستثمار والتدفقات النقدية للحصول على نتائج فورية." : "Enter investment data and cash flows for instant results."}
            </p>

            <form onSubmit={handleSubmit} className="mt-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-ink-700">
                  {ar ? "مبلغ الاستثمار (ر.س)" : "Investment amount (SAR)"}
                </label>
                <input
                  type="number"
                  value={investment}
                  onChange={(e) => setInvestment(e.target.value)}
                  placeholder={ar ? "مثال: 500000" : "e.g. 500000"}
                  data-testid="financial-investment"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-ink-700">
                  {ar ? "التدفقات النقدية السنوية (مفصولة بفواصل)" : "Annual cash flows (comma-separated)"}
                </label>
                <input
                  type="text"
                  value={cashFlowsStr}
                  onChange={(e) => setCashFlowsStr(e.target.value)}
                  placeholder={ar ? "مثال: 100000, 150000, 200000, 250000, 300000" : "e.g. 100000, 150000, 200000, 250000, 300000"}
                  data-testid="financial-cashflows"
                  className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
                <p className="mt-1 text-xs text-ink-500">{ar ? "التدفقات النقدية الصافية لكل سنة" : "Net cash flows for each year"}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-ink-700">
                  {ar ? "معدل الخصم (%)" : "Discount rate (%)"}
                </label>
                <input
                  type="number"
                  value={discountRate}
                  onChange={(e) => setDiscountRate(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                />
              </div>

              {error && <p className="text-sm text-red-600">{error}</p>}

              <button
                type="submit"
                disabled={loading}
                data-testid="run-financial-analysis"
                className="w-full rounded-xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-card transition hover:bg-brand-700 disabled:opacity-50"
              >
                {loading ? (ar ? "جارٍ التحليل..." : "Analyzing...") : (ar ? "تحليل" : "Analyze")}
              </button>
              {result && (
                <Button type="button" variant="secondary" disabled={saving} onClick={handleSave} data-testid="save-financial-analysis">
                  {saving ? (ar ? "جارٍ الحفظ..." : "Saving...") : (ar ? "حفظ التحليل كخدمة مستقلة" : "Save as an independent analysis")}
                </Button>
              )}
            </form>
          </section>

          <section className="space-y-6">
            {result ? (
              <>
                <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-ink-900">{ar ? "النتائج" : "Results"}</h2>
                    <Badge variant={result.verdict === "feasible" ? "success" : result.verdict === "not_feasible" ? "danger" : "warning"}>
                      {result.verdict === "feasible" ? (ar ? "مجدٍ" : "Feasible") : result.verdict === "not_feasible" ? (ar ? "غير مجدٍ" : "Not Feasible") : (ar ? "حدّي" : "Borderline")}
                    </Badge>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <KpiCard label={ar ? "العائد على الاستثمار" : "ROI"} value={result.roi_percent !== null ? `${result.roi_percent.toFixed(1)}%` : "—"} icon="📈" />
                  <KpiCard label={ar ? "القيمة الحالية الصافية" : "NPV"} value={result.npv !== null ? money(result.npv) : "—"} icon="💎" />
                  <KpiCard label={ar ? "معدل العائد الداخلي" : "IRR"} value={result.irr_percent !== null ? `${result.irr_percent.toFixed(1)}%` : "—"} icon="📊" />
                  <KpiCard label={ar ? "فترة الاسترداد" : "Payback"} value={result.payback_years !== null ? `${result.payback_years.toFixed(1)} ${ar ? "سنة" : "years"}` : "—"} icon="⏱️" />
                </div>
                {sensitivity != null && (
                  <p className="text-xs text-ink-500">{ar ? "تم حساب تحليل الحساسية مع النتائج." : "Sensitivity analysis was calculated with these results."}</p>
                )}
              </>
            ) : (
              <div className="flex h-full items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/50 p-12 text-center">
                <div>
                  <span className="mb-4 block text-5xl opacity-40">💰</span>
                  <p className="text-sm text-ink-500">{ar ? "أدخل بياناتك لعرض النتائج" : "Enter your data to see results"}</p>
                </div>
              </div>
            )}
          </section>
        </div>

        <section className="rounded-2xl border border-brand-200 bg-white p-6 shadow-card">
          <h2 className="text-lg font-bold text-ink-900">{ar ? "المقاييس المتاحة" : "Available metrics"}</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { title: ar ? "العائد على الاستثمار (ROI)" : "Return on Investment (ROI)", desc: ar ? "نسبة الربح الإجمالي إلى الاستثمار" : "Total profit ratio to investment" },
              { title: ar ? "القيمة الحالية الصافية (NPV)" : "Net Present Value (NPV)", desc: ar ? "القيمة الحالية لجميع التدفقات النقدية المستقبلية" : "Present value of all future cash flows" },
              { title: ar ? "معدل العائد الداخلي (IRR)" : "Internal Rate of Return (IRR)", desc: ar ? "معدل الخصم الذي يجعل NPV تساوي صفرًا" : "The discount rate at which NPV equals zero" },
              { title: ar ? "فترة الاسترداد" : "Payback Period", desc: ar ? "المدة اللازمة لاسترداد الاستثمار الأولي" : "Time to recover the initial investment" },
              { title: ar ? "نقطة التعادل" : "Break-even Point", desc: ar ? "عدد الوحدات اللازمة لتغطية التكاليف الثابتة" : "Units needed to cover fixed costs" },
              { title: ar ? "تحليل الحساسية" : "Sensitivity Analysis", desc: ar ? "كيف تتغير النتائج بتغير الافتراضات" : "How results change with different assumptions" },
            ].map((m) => (
              <div key={m.title} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                <h3 className="font-semibold text-ink-800">{m.title}</h3>
                <p className="mt-1 text-sm text-ink-600">{m.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
