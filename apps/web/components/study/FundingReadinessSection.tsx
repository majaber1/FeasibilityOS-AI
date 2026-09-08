"use client";

import {
  type ActionableStep,
  type FundingReadiness,
  type ReadinessStatus,
} from "@/lib/api";

const copy = {
  ar: {
    heading: "جاهزية التمويل",
    intro: "تقييم الفحص الداخلي لمنصة Saudi Business لمدى استعداد الشركة والملف التمويلي للتقدم لخيارات التمويل. هذا فحص جاهزية وفق معايير فحص داخلية وليس موافقة ائتمانية أو متطلبات رسمية لجهات التمويل.",
    statusLabels: {
      READY: "جاهز للتقديم",
      PARTIALLY_READY: "جاهز جزئياً",
      NEEDS_INFORMATION: "يلزم استكمال بيانات",
      NOT_READY: "غير جاهز حالياً",
    } as Record<ReadinessStatus, string>,
    positiveHeading: "عوامل إيجابية تدعم الملف",
    missingHeading: "بيانات ناقصة يلزم إدخالها",
    warningHeading: "تنبيهات وملاحظات للتحسين",
    blockingHeading: "محددات جوهرية تعيق التمويل حالياً",
    actionableHeading: "الخطوات التنفيذية التالية",
    snapshotsHeading: "مؤشرات الفحص السريع",
    healthLabel: "الصحة المالية",
    gapLabel: "فجوة التمويل",
    capacityLabel: "القدرة التمويلية التقديرية",
    collateralLabel: "الضمانات المسجّلة",
    documentsLabel: "اكتمال المستندات",
    notEvaluated: "غير مقيّم",
    sar: "ر.س",
    loading: "جارٍ فحص جاهزية التمويل...",
    takeAction: "الانتقال",
  },
  en: {
    heading: "Funding Readiness",
    intro: "Saudi Business internal screening assessment of whether the company and project are prepared to approach funding options. Evaluates readiness based on internal screening rules, not credit approval or official lender underwriting.",
    statusLabels: {
      READY: "Ready to Approach Funders",
      PARTIALLY_READY: "Partially Ready",
      NEEDS_INFORMATION: "Needs Information",
      NOT_READY: "Not Ready Currently",
    } as Record<ReadinessStatus, string>,
    positiveHeading: "Positive Supporting Factors",
    missingHeading: "Missing Information Required",
    warningHeading: "Warnings & Improvement Points",
    blockingHeading: "Material Constraints / Blockers",
    actionableHeading: "Actionable Next Steps",
    snapshotsHeading: "Screening Snapshot",
    healthLabel: "Financial Health",
    gapLabel: "Funding Gap",
    capacityLabel: "Estimated Capacity",
    collateralLabel: "Recorded Collateral",
    documentsLabel: "Document Review",
    notEvaluated: "Not Evaluated",
    sar: "SAR",
    loading: "Evaluating funding readiness...",
    takeAction: "Go to section",
  },
};

const STATUS_BADGE_STYLE: Record<ReadinessStatus, string> = {
  READY: "bg-emerald-50 text-emerald-800 border-emerald-300",
  PARTIALLY_READY: "bg-amber-50 text-amber-800 border-amber-300",
  NEEDS_INFORMATION: "bg-sky-50 text-sky-800 border-sky-300",
  NOT_READY: "bg-red-50 text-red-800 border-red-300",
};

const STATUS_BORDER_STYLE: Record<ReadinessStatus, string> = {
  READY: "border-l-emerald-500 rtl:border-l-0 rtl:border-r-emerald-500",
  PARTIALLY_READY: "border-l-amber-500 rtl:border-l-0 rtl:border-r-amber-500",
  NEEDS_INFORMATION: "border-l-sky-500 rtl:border-l-0 rtl:border-r-sky-500",
  NOT_READY: "border-l-red-500 rtl:border-l-0 rtl:border-r-red-500",
};

const TARGET_MAP: Record<string, string> = {
  financial_data: "company-financial-data",
  funding_gap: "funding-gap",
  collateral: "collateral-section",
};

type Props = {
  readiness: FundingReadiness | null;
  locale: "ar" | "en";
  loading?: boolean;
};

function fmt(n: number, locale: "ar" | "en") {
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-SA", { maximumFractionDigits: 0 }).format(n);
}

export default function FundingReadinessSection({ readiness, locale, loading }: Props) {
  const c = copy[locale];

  function scrollToSection(targetKey: string) {
    const id = TARGET_MAP[targetKey] || targetKey;
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
      el.focus?.();
    }
  }

  if (loading && !readiness) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="font-semibold text-ink-900">{c.heading}</h3>
        <p className="mt-2 text-sm text-ink-500">{c.loading}</p>
      </section>
    );
  }

  if (!readiness) {
    return null;
  }

  const isAr = locale === "ar";
  const summaryText = isAr ? readiness.summary_ar : readiness.summary_en;
  const positiveList = isAr && readiness.positive_factors_ar?.length ? readiness.positive_factors_ar : readiness.positive_factors;
  const blockingList = isAr && readiness.blocking_factors_ar?.length ? readiness.blocking_factors_ar : readiness.blocking_factors;
  const missingList = isAr && readiness.missing_information_ar?.length ? readiness.missing_information_ar : readiness.missing_information;
  const warningList = isAr && readiness.warnings_ar?.length ? readiness.warnings_ar : readiness.warnings;

  // Extract snapshot figures safely
  const gapSnapshot = readiness.funding_gap_snapshot as { funding_gap?: number } | null;
  const capacitySnapshot = readiness.borrowing_capacity_snapshot as { base_capacity?: number } | null;
  const collateralSnapshot = readiness.collateral_snapshot as { total_reported_value?: number; total_verified_value?: number } | null;
  const healthSnapshot = readiness.financial_health_snapshot as { debt_service_capacity?: string; leverage?: string } | null;

  return (
    <section
      id="funding-readiness-section"
      className={`rounded-2xl border border-slate-200 border-l-4 rtl:border-l rtl:border-r-4 ${STATUS_BORDER_STYLE[readiness.status]} bg-white p-6 shadow-sm`}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-bold text-ink-900">{c.heading}</h3>
          <p className="mt-1 text-sm text-ink-600">{c.intro}</p>
        </div>
        <span
          className={`inline-flex items-center rounded-full border px-3.5 py-1 text-sm font-semibold ${STATUS_BADGE_STYLE[readiness.status]}`}
        >
          {c.statusLabels[readiness.status]}
        </span>
      </div>

      <div className="mt-4 rounded-xl bg-slate-50 p-4">
        <p className="text-sm font-medium text-ink-900 leading-relaxed">{summaryText}</p>
      </div>

      {/* Quick Snapshots Bar */}
      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-xs text-ink-500">{c.healthLabel}</p>
          <p className="mt-1 text-sm font-semibold text-ink-900">
            {healthSnapshot?.debt_service_capacity ? `DSCR: ${healthSnapshot.debt_service_capacity}` : "—"}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-xs text-ink-500">{c.gapLabel}</p>
          <p className="mt-1 text-sm font-semibold text-ink-900">
            {gapSnapshot?.funding_gap !== undefined ? `${fmt(gapSnapshot.funding_gap, locale)} ${c.sar}` : "—"}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-xs text-ink-500">{c.capacityLabel}</p>
          <p className="mt-1 text-sm font-semibold text-ink-900">
            {capacitySnapshot?.base_capacity !== undefined && capacitySnapshot.base_capacity !== null
              ? `${fmt(capacitySnapshot.base_capacity, locale)} ${c.sar}`
              : "—"}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-xs text-ink-500">{c.collateralLabel}</p>
          <p className="mt-1 text-sm font-semibold text-ink-900">
            {collateralSnapshot?.total_reported_value !== undefined
              ? `${fmt(collateralSnapshot.total_reported_value, locale)} ${c.sar}`
              : "0 " + c.sar}
          </p>
          {collateralSnapshot?.total_verified_value !== undefined && collateralSnapshot.total_verified_value > 0 ? (
            <p className="text-xs text-emerald-700 mt-0.5">
              {isAr
                ? `موثّق: ${fmt(collateralSnapshot.total_verified_value, locale)} ${c.sar}`
                : `Verified: ${fmt(collateralSnapshot.total_verified_value, locale)} ${c.sar}`}
            </p>
          ) : (
            <p className="text-xs text-slate-400 mt-0.5">
              {isAr ? "غير موثّق مستقلاً" : "Not verified"}
            </p>
          )}
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          <p className="text-xs text-ink-500">{c.documentsLabel}</p>
          <p className="mt-1 text-sm font-semibold text-ink-600">{c.notEvaluated}</p>
        </div>
      </div>

      {/* Blockers Grid (if any) */}
      {blockingList.length > 0 && (
        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 p-4">
          <h4 className="font-semibold text-red-900 flex items-center gap-2">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-red-200 text-red-800 text-xs font-bold">✕</span>
            {c.blockingHeading}
          </h4>
          <ul className="mt-2.5 space-y-1.5 text-sm text-red-800">
            {blockingList.map((factor, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="font-bold">•</span>
                <span>{factor}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Factors / Missing / Warnings Details */}
      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        {/* Positive Factors */}
        {positiveList.length > 0 && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4">
            <h4 className="font-semibold text-emerald-900 flex items-center gap-2">
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-200 text-emerald-800 text-xs font-bold">✓</span>
              {c.positiveHeading}
            </h4>
            <ul className="mt-2.5 space-y-1.5 text-sm text-emerald-900">
              {positiveList.map((factor, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="font-bold text-emerald-600">✓</span>
                  <span>{factor}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Missing Information */}
        {missingList.length > 0 && (
          <div className="rounded-xl border border-sky-200 bg-sky-50/60 p-4">
            <h4 className="font-semibold text-sky-900 flex items-center gap-2">
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-sky-200 text-sky-800 text-xs font-bold">!</span>
              {c.missingHeading}
            </h4>
            <ul className="mt-2.5 space-y-1.5 text-sm text-sky-900">
              {missingList.map((info, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="font-bold text-sky-600">•</span>
                  <span>{info}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Warnings */}
        {warningList.length > 0 && (
          <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-4 lg:col-span-2">
            <h4 className="font-semibold text-amber-900 flex items-center gap-2">
              <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-amber-200 text-amber-800 text-xs font-bold">⚠</span>
              {c.warningHeading}
            </h4>
            <ul className="mt-2.5 space-y-1.5 text-sm text-amber-900">
              {warningList.map((warning, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="font-bold text-amber-600">•</span>
                  <span>{warning}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Actionable Next Steps */}
      {readiness.actionable_steps && readiness.actionable_steps.length > 0 && (
        <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <h4 className="font-semibold text-ink-900 text-sm">{c.actionableHeading}</h4>
          <div className="mt-3 flex flex-wrap gap-2.5">
            {readiness.actionable_steps.map((step: ActionableStep) => (
              <button
                key={step.key}
                type="button"
                onClick={() => scrollToSection(step.action_target)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-brand-300 bg-white px-3 py-1.5 text-xs font-medium text-brand-700 shadow-sm hover:bg-brand-50 hover:text-brand-800 transition-colors"
              >
                <span>{isAr ? step.title_ar : step.title_en}</span>
                <span className="text-ink-400">→</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
