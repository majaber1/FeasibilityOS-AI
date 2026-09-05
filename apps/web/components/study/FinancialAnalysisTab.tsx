"use client";

import { useEffect, useState } from "react";
import { computeStudyFromAssumptions, listAssumptions, type Study } from "@/lib/api";

export default function FinancialAnalysisTab({ token, study, locale, onComputed }: {
  token: string; study: Study; locale: "ar" | "en"; onComputed: () => Promise<void>;
}) {
  const ar = locale === "ar";
  const [missing, setMissing] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    listAssumptions(token, study.id).then((rows) => {
      if (active) setMissing(["capex", "revenue_year1"].filter((key) => !rows.some((row) => row.key === key && row.value_number != null)));
    }).catch((reason) => { if (active) setError(String(reason)); });
    return () => { active = false; };
  }, [token, study.id]);

  async function compute() {
    setBusy(true); setError("");
    try { await computeStudyFromAssumptions(token, study.id); await onComputed(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  }
  return <div className="mt-5 space-y-4" data-testid="financial-analysis-workspace">
    <p>{ar ? "تُحسب النتائج من افتراضات الدراسة المحفوظة، وليست حقائق سوقية موثقة." : "Results are calculated from saved study assumptions, not verified market facts."}</p>
    {missing === null ? <p>{ar ? "جارٍ تحميل الافتراضات..." : "Loading assumptions..."}</p> : missing.length > 0 ? <p>{ar ? "أضف الافتراضات المطلوبة:" : "Add required assumptions:"} {missing.join(", ")}</p> : null}
    <button className="rounded-lg bg-brand-600 px-4 py-2 text-white disabled:opacity-50" disabled={busy || missing === null || missing.length > 0} onClick={() => void compute()} data-testid="compute-saved-assumptions">
      {busy ? (ar ? "جارٍ الحساب..." : "Computing...") : (ar ? "احسب من الافتراضات المحفوظة" : "Compute from saved assumptions")}
    </button>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    {study.result && <div data-testid="financial-analysis-result" className="space-y-2 rounded-xl bg-slate-50 p-4">
      <p>{ar ? "نتائج مشتقة من المنصة" : "Platform-derived results"} · FORECAST</p>
      {([ ["NPV (SAR)", study.result.npv], ["ROI (%)", study.result.roi_percent], ["IRR (%)", study.result.irr_percent], [ar ? "الاسترداد (سنوات)" : "Payback (years)", study.result.payback_years] ] as const).map(([label, value]) => <p key={label}>{label}: {value == null ? "UNKNOWN" : new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value)}</p>)}
      <p>{study.result.verdict}</p>
    </div>}
  </div>;
}
