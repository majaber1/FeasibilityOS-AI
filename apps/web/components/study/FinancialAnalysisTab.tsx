"use client";

import { useEffect, useState } from "react";
import { computeStudyFromAssumptions, listAssumptions, type Study } from "@/lib/api";

const IRR_UNAVAILABLE_EN =
  "IRR cannot be calculated for these cash flows (no valid internal rate of return in range).";
const IRR_UNAVAILABLE_AR =
  "لا يمكن حساب معدل العائد الداخلي لهذه التدفقات النقدية (لا يوجد معدل عائد داخلي صالح ضمن النطاق).";

function formatIrr(result: NonNullable<Study["result"]>, locale: "ar" | "en"): string {
  if (result.irr_display) return result.irr_display;
  if (result.irr_percent == null) {
    return locale === "ar" ? IRR_UNAVAILABLE_AR : IRR_UNAVAILABLE_EN;
  }
  return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(result.irr_percent)}%`;
}

export default function FinancialAnalysisTab({
  token,
  study,
  locale,
  onComputed,
  onOpenAssumptions,
}: {
  token: string;
  study: Study;
  locale: "ar" | "en";
  onComputed: () => Promise<void>;
  onOpenAssumptions?: () => void;
}) {
  const ar = locale === "ar";
  const [missing, setMissing] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    listAssumptions(token, study.id)
      .then((rows) => {
        if (active) {
          setMissing(
            ["capex", "revenue_year1"].filter(
              (key) => !rows.some((row) => row.key === key && row.value_number != null),
            ),
          );
        }
      })
      .catch((reason) => {
        if (active) setError(String(reason));
      });
    return () => {
      active = false;
    };
  }, [token, study.id]);

  async function compute() {
    setBusy(true);
    setError("");
    try {
      await computeStudyFromAssumptions(token, study.id);
      await onComputed();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  const warnings = study.result?.warnings ?? [];

  return (
    <div className="mt-5 space-y-4" data-testid="financial-analysis-workspace">
      <p>
        {ar
          ? "تُحسب النتائج من افتراضات الدراسة المحفوظة، وليست حقائق سوقية موثقة."
          : "Results are calculated from saved study assumptions, not verified market facts."}
      </p>
      {missing === null ? (
        <p>{ar ? "جارٍ تحميل الافتراضات..." : "Loading assumptions..."}</p>
      ) : missing.length > 0 ? (
        <p data-testid="missing-assumptions">
          {ar ? "أضف الافتراضات المطلوبة:" : "Add required assumptions:"} {missing.join(", ")}
        </p>
      ) : null}
      {onOpenAssumptions ? (
        <button
          type="button"
          onClick={onOpenAssumptions}
          data-testid="open-assumptions-from-financial"
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm"
        >
          {ar ? "العودة إلى الافتراضات" : "Back to assumptions"}
        </button>
      ) : null}
      <button
        className="rounded-lg bg-brand-600 px-4 py-2 text-white disabled:opacity-50"
        disabled={busy || missing === null || missing.length > 0}
        onClick={() => void compute()}
        data-testid="compute-saved-assumptions"
      >
        {busy
          ? ar
            ? "جارٍ الحساب..."
            : "Computing..."
          : ar
            ? "احسب من الافتراضات المحفوظة"
            : "Compute from saved assumptions"}
      </button>
      {error && (
        <p role="alert" className="text-red-700">
          {error}
        </p>
      )}
      {study.result && (
        <div data-testid="financial-analysis-result" className="space-y-2 rounded-xl bg-slate-50 p-4">
          <p>{ar ? "نتائج مشتقة من المنصة" : "Platform-derived results"} · FORECAST</p>
          <p data-testid="metric-NPV (SAR)">
            NPV (SAR):{" "}
            {study.result.npv == null
              ? "—"
              : new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(study.result.npv)}
          </p>
          <p data-testid="metric-ROI (%)">
            ROI (%):{" "}
            {study.result.roi_percent == null
              ? "—"
              : new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(
                  study.result.roi_percent,
                )}
          </p>
          <p data-testid="metric-IRR (%)">IRR: {formatIrr(study.result, locale)}</p>
          <p data-testid={`metric-${ar ? "الاسترداد (سنوات)" : "Payback (years)"}`}>
            {ar ? "الاسترداد (سنوات)" : "Payback (years)"}:{" "}
            {study.result.payback_years == null
              ? "—"
              : new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(
                  study.result.payback_years,
                )}
          </p>
          <p>{study.result.verdict}</p>
          {warnings.length > 0 && (
            <ul
              data-testid="financial-input-warnings"
              className="mt-2 space-y-1 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
            >
              {warnings.map((w) => (
                <li key={w}>⚠ {w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
