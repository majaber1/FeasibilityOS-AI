"use client";

import { formatIrrMetric, formatPaybackMetric } from "@/lib/financialDisplay";

type FinancialResults = Record<string, unknown> | null | undefined;

type Props = {
  ar: boolean;
  phase: string;
  loading: boolean;
  financial: FinancialResults;
  risks?: string[];
  verdict?: string | null;
  rationale?: string | null;
  conditions?: string[];
  onContinue: () => void;
};

const STEPS = [
  { id: "classification", phases: ["ARCHETYPE_CLASSIFICATION"], ar: "التصنيف", en: "Classification" },
  { id: "discovery", phases: ["NEEDS_INFORMATION", "UNDERSTANDING", "EVIDENCE_REVIEW"], ar: "الاكتشاف", en: "Discovery" },
  { id: "assumptions", phases: ["ASSUMPTIONS_REVIEW"], ar: "الافتراضات", en: "Assumptions" },
  { id: "financial", phases: ["READY_FOR_ANALYSIS", "ANALYZED"], ar: "المالي", en: "Financial" },
  { id: "risks", phases: ["DECISION_READY"], ar: "المخاطر", en: "Risks" },
  { id: "decision", phases: ["DECISION_READY", "REPORT_READY"], ar: "القرار", en: "Decision" },
  { id: "report", phases: ["REPORT_READY"], ar: "التقرير", en: "Report" },
] as const;

function stepIndex(phase: string): number {
  if (phase === "REPORT_READY") return 6;
  if (phase === "DECISION_READY") return 4; // risks panel + continue to decision
  if (phase === "ANALYZED" || phase === "READY_FOR_ANALYSIS") return 3;
  if (phase === "ASSUMPTIONS_REVIEW") return 2;
  if (phase === "NEEDS_INFORMATION" || phase === "UNDERSTANDING" || phase === "EVIDENCE_REVIEW") return 1;
  if (phase === "ARCHETYPE_CLASSIFICATION") return 0;
  return 0;
}

function metric(financial: FinancialResults, key: string): string | null {
  if (!financial || !(key in financial)) return null;
  const value = financial[key];
  if (value === null || value === undefined || value === "") return null;
  const text = String(value).trim();
  if (!text || text.toLowerCase() === "null" || text.toLowerCase() === "undefined") return null;
  return text;
}

function MetricCard({
  label,
  display,
  available,
  reason,
  missingCondition,
}: {
  label: string;
  display: string;
  available?: boolean;
  reason?: string | null;
  missingCondition?: string | null;
}) {
  return (
    <div className="rounded-lg bg-white p-2" data-available={available ? "true" : "false"}>
      <span className="text-ink-500">{label}</span>
      <p className="font-semibold">{display}</p>
      {!available && reason ? <p className="mt-1 text-[11px] leading-snug text-ink-600">{reason}</p> : null}
      {!available && missingCondition ? (
        <p className="mt-0.5 text-[11px] leading-snug text-ink-500">{missingCondition}</p>
      ) : null}
    </div>
  );
}

export function StudyJourneyNav({ ar, phase }: { ar: boolean; phase: string }) {
  const active = stepIndex(phase);
  return (
    <nav
      className="mb-3 overflow-x-auto rounded-xl border border-slate-200 bg-white p-2"
      data-testid="study-journey-nav"
      aria-label={ar ? "مراحل الدراسة" : "Study journey"}
    >
      <ol className="flex min-w-max items-center gap-1">
        {STEPS.map((step, idx) => {
          const done = idx < active || (phase === "REPORT_READY" && idx <= 6);
          const current = idx === active;
          return (
            <li key={step.id} className="flex items-center gap-1">
              <span
                data-testid={`journey-step-${step.id}`}
                data-active={current ? "true" : "false"}
                className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${
                  current
                    ? "bg-brand-600 text-white"
                    : done
                      ? "bg-emerald-50 text-emerald-800"
                      : "bg-slate-100 text-slate-500"
                }`}
              >
                {ar ? step.ar : step.en}
              </span>
              {idx < STEPS.length - 1 ? <span className="text-slate-300">›</span> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export function StudyLateStagePanels({
  ar,
  phase,
  loading,
  financial,
  risks = [],
  verdict,
  rationale,
  conditions = [],
  onContinue,
}: Props) {
  const showFinancial = phase === "READY_FOR_ANALYSIS" || phase === "ANALYZED";
  const showRisks = phase === "DECISION_READY";
  const showReport = phase === "REPORT_READY";
  const canContinue = phase === "READY_FOR_ANALYSIS" || phase === "ANALYZED" || phase === "DECISION_READY";

  if (!showFinancial && !showRisks && !showReport) return null;

  const npv = metric(financial, "npv");
  const irrMetric = formatIrrMetric(financial, ar);
  const paybackMetric = formatPaybackMetric(financial, ar);
  const capex = metric(financial, "capex");
  const warnings = Array.isArray(financial?.warnings)
    ? (financial!.warnings as unknown[]).map((w) => String(w)).filter(Boolean)
    : [];

  return (
    <div className="mb-3 space-y-3" data-testid="study-late-stage-panels">
      {showFinancial ? (
        <section
          className="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4"
          data-testid="in-study-financial-panel"
        >
          <h2 className="text-sm font-bold text-ink-900">
            {ar ? "التحليل المالي داخل الدراسة" : "In-study financial analysis"}
          </h2>
          <p className="mt-1 text-xs text-ink-600">
            {ar
              ? "هذه النتائج مبنية على افتراضات هذه الدراسة — وليست الآلة الحاسبة المستقلة."
              : "These results come from this study’s assumptions — not the standalone calculator."}
          </p>
          {phase === "READY_FOR_ANALYSIS" && !financial ? (
            <p className="mt-3 text-sm text-ink-700">
              {ar ? "الافتراضات معتمدة. شغّل التحليل المالي للمتابعة." : "Assumptions approved. Run financial analysis to continue."}
            </p>
          ) : (
            <>
              <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4 text-sm">
                {npv ? (
                  <div className="rounded-lg bg-white p-2">
                    <span className="text-ink-500">NPV</span>
                    <p className="font-semibold">{npv}</p>
                  </div>
                ) : null}
                <MetricCard
                  label={irrMetric.label || "IRR"}
                  display={irrMetric.display || ""}
                  available={irrMetric.available}
                  reason={irrMetric.reason}
                  missingCondition={irrMetric.missing_condition}
                />
                <MetricCard
                  label={paybackMetric.label || (ar ? "فترة الاسترداد" : "Payback Period")}
                  display={paybackMetric.display || ""}
                  available={paybackMetric.available}
                  reason={paybackMetric.reason}
                  missingCondition={paybackMetric.missing_condition}
                />
                {capex ? (
                  <div className="rounded-lg bg-white p-2">
                    <span className="text-ink-500">CAPEX</span>
                    <p className="font-semibold">{capex}</p>
                  </div>
                ) : null}
              </div>
              {warnings.length > 0 ? (
                <ul
                  data-testid="in-study-financial-warnings"
                  className="mt-3 space-y-1 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"
                >
                  {warnings.map((w) => (
                    <li key={w}>⚠ {w}</li>
                  ))}
                </ul>
              ) : null}
            </>
          )}
          <button
            type="button"
            data-testid="continue-to-risks-btn"
            disabled={loading}
            onClick={onContinue}
            className="mt-3 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {loading
              ? ar
                ? "جارٍ المتابعة..."
                : "Continuing..."
              : phase === "READY_FOR_ANALYSIS"
                ? ar
                  ? "تشغيل التحليل المالي"
                  : "Run financial analysis"
                : ar
                  ? "المتابعة إلى المخاطر"
                  : "Continue to risks"}
          </button>
        </section>
      ) : null}

      {showRisks ? (
        <section className="rounded-xl border border-amber-200 bg-amber-50/50 p-4" data-testid="in-study-risks-panel">
          <h2 className="text-sm font-bold text-ink-900">{ar ? "المخاطر" : "Risks"}</h2>
          {risks.length > 0 ? (
            <ul className="mt-2 list-disc space-y-1 ps-5 text-sm text-ink-800">
              {risks.map((risk) => (
                <li key={risk}>{risk}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-sm text-ink-600">
              {ar ? "تم تحليل المخاطر. تابع لإصدار القرار." : "Risk analysis complete. Continue to issue the decision."}
            </p>
          )}
          <button
            type="button"
            data-testid="continue-to-decision-btn"
            disabled={loading}
            onClick={onContinue}
            className="mt-3 rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
          >
            {loading ? (ar ? "جارٍ المتابعة..." : "Continuing...") : ar ? "المتابعة إلى القرار والتقرير" : "Continue to decision & report"}
          </button>
        </section>
      ) : null}

      {showReport ? (
        <section className="rounded-xl border border-brand-200 bg-brand-50/40 p-4" data-testid="in-study-report-panel">
          <h2 className="text-sm font-bold text-ink-900">{ar ? "التقرير النهائي" : "Final report"}</h2>
          {verdict ? (
            <p className="mt-2 text-sm font-semibold text-ink-900" data-testid="report-verdict">
              {ar ? "القرار:" : "Verdict:"} {verdict}
            </p>
          ) : null}
          {rationale ? (
            <p className="mt-2 whitespace-pre-wrap text-sm text-ink-800" data-testid="report-rationale">
              {rationale}
            </p>
          ) : null}
          {conditions.length > 0 ? (
            <div className="mt-3">
              <p className="text-xs font-semibold text-ink-600">{ar ? "الشروط" : "Conditions"}</p>
              <ul className="mt-1 list-disc ps-5 text-sm text-ink-700">
                {conditions.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {risks.length > 0 ? (
            <div className="mt-3">
              <p className="text-xs font-semibold text-ink-600">{ar ? "ملخص المخاطر" : "Risk summary"}</p>
              <ul className="mt-1 list-disc ps-5 text-sm text-ink-700">
                {risks.map((risk) => (
                  <li key={risk}>{risk}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {(npv || irrMetric.display || paybackMetric.display) && (
            <div className="mt-3 grid gap-2 sm:grid-cols-3 text-sm">
              {npv ? <div className="rounded-lg bg-white p-2">NPV: <strong>{npv}</strong></div> : null}
              <div className="rounded-lg bg-white p-2">
                {irrMetric.label}: <strong>{irrMetric.display}</strong>
                {!irrMetric.available && irrMetric.reason ? (
                  <p className="mt-1 text-[11px] text-ink-600">{irrMetric.reason}</p>
                ) : null}
              </div>
              <div className="rounded-lg bg-white p-2">
                {paybackMetric.label}: <strong>{paybackMetric.display}</strong>
                {!paybackMetric.available && paybackMetric.reason ? (
                  <p className="mt-1 text-[11px] text-ink-600">{paybackMetric.reason}</p>
                ) : null}
              </div>
            </div>
          )}
          <button
            type="button"
            data-testid="print-report-btn"
            onClick={() => window.print()}
            className="mt-3 rounded-lg border border-brand-300 bg-white px-4 py-2 text-sm font-semibold text-brand-800 hover:bg-brand-50"
          >
            {ar ? "طباعة / حفظ التقرير" : "Print / save report"}
          </button>
        </section>
      ) : null}
    </div>
  );
}
