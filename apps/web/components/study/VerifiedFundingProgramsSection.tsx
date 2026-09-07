"use client";

import { useCallback, useEffect, useState } from "react";
import {
  listFundingPrograms,
  getFundingProgramsSummary,
  type FundingProgram,
  type FundingProgramRule,
  type RegistrySummary,
} from "@/lib/api";

type Props = {
  token?: string;
  locale?: string;
};

const copy = {
  ar: {
    heading: "سجل برامج التمويل المعتمدة",
    subheading:
      "برامج تمويل وتسهيلات ائتمانية رسمية معتمدة من الصناديق والبنوك التنموية السعودية، مع قواعد استحقاق موثقة بدقة ومربوطة بمصادرها النظامية (.gov.sa). لا توجد نسب عشوائية أو شروط مختلقة.",
    summaryTitle: "ملخص السجل المعتمد",
    totalPrograms: "إجمالي البرامج",
    verifiedStatus: "حالة التحقق",
    allVerified: "موثّق رسميًا وفعّال",
    providersCount: "الجهات التمويلية",
    filterProvider: "الجهة التمويلية",
    allProviders: "جميع الجهات",
    filterType: "نوع البرنامج",
    allTypes: "جميع الأنواع",
    loading: "جارٍ تحميل البرامج التمويلية المعتمدة...",
    error: "تعذر تحميل البرامج التمويلية.",
    empty: "لا توجد برامج مطابقة لمعايير الفلترة المحددة.",
    financingRange: "نطاق التمويل",
    upTo: "حتى",
    sar: "ر.س",
    months: "شهرًا",
    term: "مدة التمويل",
    gracePeriod: "فترة السماح",
    targetStage: "المرحلة المستهدفة",
    targetSectors: "القطاعات المستهدفة",
    ownerContribution: "مساهمة المالك",
    collateralRequirement: "متطلبات الضمان",
    guaranteeTerms: "شروط الكفالة",
    officialSource: "المصدر الرسمي",
    viewEvidence: "عرض القواعد والأدلة الموثّقة",
    evidenceTitle: "سجل الأدلة والقواعد الموثقة للبرنامج",
    evidenceSubtitle: "تفاصيل السند النظامي والمصدر الحكومي لكل معيار وقيد في هذا البرنامج",
    ruleKey: "المعيار / القاعدة",
    ruleType: "نوع القاعدة",
    ruleDescription: "النص / التفصيل",
    sourceReference: "السند / المرجع النظامي",
    sourceAuthority: "المرجع المعتمد",
    sourceUrl: "رابط اللائحة الرسمية",
    ruleVersion: "إصدار القاعدة",
    verifiedAt: "تاريخ التحقق",
    close: "إغلاق",
    typeLabels: {
      DIRECT_LOAN: "قرض / تمويل مباشر",
      GUARANTEE: "كفالة ائتمانية",
      WORKING_CAPITAL: "رأس مال عامل",
      CO_FINANCING: "تمويل مشترك",
      GRANT: "منحة",
    } as Record<string, string>,
    stageLabels: {
      STARTUP: "مشاريع ناشئة جديدة",
      EXISTING: "منشآت قائمة",
      EXPANSION: "توسع ونمو",
      ALL: "كافة المراحل (ناشئة وقائمة)",
    } as Record<string, string>,
  },
  en: {
    heading: "Verified Saudi Funding Programs Registry",
    subheading:
      "Official funding programs and credit guarantees from Saudi development finance institutions with verified eligibility rules linked directly to official regulatory sources (.gov.sa). No fabricated eligibility scores or assumptions.",
    summaryTitle: "Verified Registry Summary",
    totalPrograms: "Total Programs",
    verifiedStatus: "Verification Status",
    allVerified: "Officially Verified & Active",
    providersCount: "Funding Providers",
    filterProvider: "Provider",
    allProviders: "All Providers",
    filterType: "Program Type",
    allTypes: "All Types",
    loading: "Loading verified funding programs...",
    error: "Failed to load funding programs.",
    empty: "No funding programs match the selected criteria.",
    financingRange: "Financing Range",
    upTo: "Up to",
    sar: "SAR",
    months: "months",
    term: "Financing Term",
    gracePeriod: "Grace Period",
    targetStage: "Target Stage",
    targetSectors: "Target Sectors",
    ownerContribution: "Owner Equity",
    collateralRequirement: "Collateral Requirement",
    guaranteeTerms: "Guarantee Terms",
    officialSource: "Official Portal",
    viewEvidence: "View Verified Rules & Evidence",
    evidenceTitle: "Program Rules & Regulatory Provenance",
    evidenceSubtitle: "Exact regulatory citation and official government source for each criterion in this program",
    ruleKey: "Rule Key",
    ruleType: "Rule Type",
    ruleDescription: "Description / Details",
    sourceReference: "Regulatory Citation / Section",
    sourceAuthority: "Authority",
    sourceUrl: "Official Regulation URL",
    ruleVersion: "Rule Version",
    verifiedAt: "Verified At",
    close: "Close",
    typeLabels: {
      DIRECT_LOAN: "Direct Loan",
      GUARANTEE: "Credit Guarantee",
      WORKING_CAPITAL: "Working Capital",
      CO_FINANCING: "Co-Financing",
      GRANT: "Grant",
    } as Record<string, string>,
    stageLabels: {
      STARTUP: "Startups / New Ventures",
      EXISTING: "Existing Enterprises",
      EXPANSION: "Expansion & Growth",
      ALL: "All Stages (Startup & Existing)",
    } as Record<string, string>,
  },
};

function formatMoney(val: number | null | undefined, locale: string): string {
  if (val === null || val === undefined) return "—";
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-US").format(val);
}

export default function VerifiedFundingProgramsSection({ token, locale = "ar" }: Props) {
  const c = locale === "en" ? copy.en : copy.ar;

  const [programs, setPrograms] = useState<FundingProgram[]>([]);
  const [summary, setSummary] = useState<RegistrySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedProvider, setSelectedProvider] = useState<string>("");
  const [selectedType, setSelectedType] = useState<string>("");

  // Modal inspection
  const [activeProgram, setActiveProgram] = useState<FundingProgram | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [progList, regSummary] = await Promise.all([
        listFundingPrograms(token, {
          provider: selectedProvider || undefined,
          program_type: selectedType || undefined,
        }),
        getFundingProgramsSummary(token),
      ]);
      setPrograms(progList);
      setSummary(regSummary);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : c.error);
    } finally {
      setLoading(false);
    }
  }, [token, selectedProvider, selectedType, c.error]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <section id="verified-funding-programs" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500 ring-4 ring-emerald-100" />
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700">
              Wave 2 — Funding Intelligence
            </span>
          </div>
          <h2 className="mt-1 text-xl font-bold text-ink-900">{c.heading}</h2>
          <p className="mt-1 max-w-3xl text-sm text-ink-600 leading-relaxed">{c.subheading}</p>
        </div>
      </div>

      {/* Summary KPI Bar */}
      {summary && (
        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-3">
            <p className="text-xs font-medium text-ink-500">{c.totalPrograms}</p>
            <p className="mt-1 text-xl font-bold text-ink-900">{summary.total_programs}</p>
          </div>
          <div className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-3">
            <p className="text-xs font-medium text-emerald-700">{c.verifiedStatus}</p>
            <p className="mt-1 text-sm font-bold text-emerald-800">{c.allVerified}</p>
          </div>
          <div className="rounded-xl border border-slate-100 bg-slate-50/80 p-3">
            <p className="text-xs font-medium text-ink-500">{c.providersCount}</p>
            <p className="mt-1 text-xl font-bold text-ink-900">{summary.all_providers.length}</p>
          </div>
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/60 p-3">
            <p className="text-xs font-medium text-indigo-700">
              {locale === "ar" ? "قروض وضمانات" : "Loans & Guarantees"}
            </p>
            <p className="mt-1 text-sm font-semibold text-indigo-900">
              {(summary.program_types_breakdown.DIRECT_LOAN || 0) + (summary.program_types_breakdown.WORKING_CAPITAL || 0)}{" "}
              {locale === "ar" ? "تمويل" : "Debt"} / {summary.program_types_breakdown.GUARANTEE || 0}{" "}
              {locale === "ar" ? "كفالة" : "Guar."}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mt-6 flex flex-wrap items-center gap-3 border-y border-slate-100 py-3">
        <div className="flex items-center gap-2">
          <label htmlFor="filter-provider" className="text-xs font-medium text-ink-600">
            {c.filterProvider}:
          </label>
          <select
            id="filter-provider"
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-ink-800 shadow-sm focus:border-brand-500 focus:outline-none"
          >
            <option value="">{c.allProviders}</option>
            {summary?.all_providers.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="filter-type" className="text-xs font-medium text-ink-600">
            {c.filterType}:
          </label>
          <select
            id="filter-type"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-ink-800 shadow-sm focus:border-brand-500 focus:outline-none"
          >
            <option value="">{c.allTypes}</option>
            <option value="DIRECT_LOAN">{c.typeLabels.DIRECT_LOAN}</option>
            <option value="GUARANTEE">{c.typeLabels.GUARANTEE}</option>
            <option value="WORKING_CAPITAL">{c.typeLabels.WORKING_CAPITAL}</option>
            <option value="CO_FINANCING">{c.typeLabels.CO_FINANCING}</option>
          </select>
        </div>

        {(selectedProvider || selectedType) && (
          <button
            type="button"
            onClick={() => {
              setSelectedProvider("");
              setSelectedType("");
            }}
            className="text-xs text-brand-600 hover:text-brand-800 hover:underline"
          >
            {locale === "ar" ? "إعادة ضبط الفلاتر" : "Reset filters"}
          </button>
        )}
      </div>

      {/* Program Cards Grid */}
      {loading ? (
        <div className="py-12 text-center text-sm text-ink-500">{c.loading}</div>
      ) : error ? (
        <div className="my-4 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {error}
        </div>
      ) : programs.length === 0 ? (
        <div className="py-12 text-center text-sm text-ink-500">{c.empty}</div>
      ) : (
        <div className="mt-6 grid gap-5 lg:grid-cols-2">
          {programs.map((prog) => {
            const minAmt = prog.financing_min;
            const maxAmt = prog.financing_max;

            return (
              <article
                key={prog.id}
                className="flex flex-col justify-between rounded-xl border border-slate-200/90 bg-white p-5 shadow-xs transition hover:border-brand-300 hover:shadow-sm"
              >
                <div>
                  {/* Card Header */}
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <span className="inline-block rounded-md bg-slate-100 px-2.5 py-1 text-xs font-semibold text-ink-700">
                        {locale === "ar" ? prog.provider_ar : prog.provider}
                      </span>
                      <span className="ml-2 mr-2 inline-block rounded-md bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                        {c.typeLabels[prog.program_type] || prog.program_type}
                      </span>
                    </div>

                    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                      ✓ {locale === "ar" ? "موثّق رسميًا" : "VERIFIED"}
                    </span>
                  </div>

                  {/* Title & Description */}
                  <h3 className="mt-3 text-base font-bold text-ink-900 leading-snug">
                    {locale === "ar" ? prog.program_name_ar : prog.program_name_en}
                  </h3>
                  <p className="mt-1.5 text-xs text-ink-600 line-clamp-2 leading-relaxed">
                    {locale === "ar" ? prog.description_ar : prog.description_en}
                  </p>

                  {/* Financial & Terms Highlights */}
                  <div className="mt-4 grid grid-cols-2 gap-2 rounded-lg bg-slate-50/70 p-3 text-xs">
                    <div>
                      <span className="text-ink-500">{c.financingRange}:</span>
                      <p className="mt-0.5 font-bold text-ink-900">
                        {minAmt && maxAmt
                          ? `${formatMoney(minAmt, locale)} - ${formatMoney(maxAmt, locale)} ${c.sar}`
                          : maxAmt
                          ? `${c.upTo} ${formatMoney(maxAmt, locale)} ${c.sar}`
                          : "—"}
                      </p>
                    </div>

                    <div>
                      <span className="text-ink-500">{c.term}:</span>
                      <p className="mt-0.5 font-bold text-ink-900">
                        {prog.term_months
                          ? `${prog.term_months} ${c.months} ${
                              prog.grace_period_months
                                ? `(${c.gracePeriod}: ${prog.grace_period_months} ${c.months})`
                                : ""
                            }`
                          : "—"}
                      </p>
                    </div>

                    <div className="col-span-2 pt-1 border-t border-slate-100">
                      <span className="text-ink-500">{c.targetStage}: </span>
                      <span className="font-medium text-ink-800">
                        {c.stageLabels[prog.target_business_stage] || prog.target_business_stage}
                      </span>
                    </div>
                  </div>

                  {/* Structured Key Rules Snippet */}
                  <div className="mt-3 space-y-1.5 text-xs text-ink-700">
                    {prog.owner_contribution_rule && (
                      <div className="flex items-baseline gap-1.5">
                        <span className="font-semibold text-brand-800">• {c.ownerContribution}:</span>
                        <span>
                          {locale === "ar"
                            ? (prog.owner_contribution_rule as Record<string, string>).description_ar
                            : (prog.owner_contribution_rule as Record<string, string>).description_en ||
                              JSON.stringify(prog.owner_contribution_rule)}
                        </span>
                      </div>
                    )}
                    {prog.collateral_rule && (
                      <div className="flex items-baseline gap-1.5">
                        <span className="font-semibold text-amber-800">• {c.collateralRequirement}:</span>
                        <span>
                          {locale === "ar"
                            ? (prog.collateral_rule as Record<string, string>).description_ar
                            : (prog.collateral_rule as Record<string, string>).description_en ||
                              JSON.stringify(prog.collateral_rule)}
                        </span>
                      </div>
                    )}
                    {prog.guarantee_rule && (
                      <div className="flex items-baseline gap-1.5">
                        <span className="font-semibold text-indigo-800">• {c.guaranteeTerms}:</span>
                        <span>
                          {locale === "ar"
                            ? (prog.guarantee_rule as Record<string, string>).description_ar
                            : (prog.guarantee_rule as Record<string, string>).description_en ||
                              JSON.stringify(prog.guarantee_rule)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions & Provenance Link */}
                <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3 text-xs">
                  <a
                    href={prog.official_source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 font-medium text-brand-600 hover:text-brand-800 hover:underline"
                  >
                    <span>↗</span>
                    <span>{c.officialSource}</span>
                  </a>

                  <button
                    type="button"
                    onClick={() => setActiveProgram(prog)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-medium text-ink-800 shadow-xs hover:bg-slate-50 focus:outline-none"
                  >
                    <span>🛡️</span>
                    <span>{c.viewEvidence}</span>
                    <span className="rounded-full bg-slate-100 px-1.5 py-0.2 text-[10px] font-bold text-ink-600">
                      {prog.rules.length}
                    </span>
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* Rules & Evidence Provenance Modal */}
      {activeProgram && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs"
        >
          <div className="flex max-h-[90vh] w-full max-w-2xl flex-col rounded-2xl bg-white shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-100 p-5">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-800">
                    {locale === "ar" ? activeProgram.provider_ar : activeProgram.provider}
                  </span>
                  <span className="text-xs text-ink-500">v{activeProgram.rule_version}</span>
                </div>
                <h3 className="mt-1.5 text-lg font-bold text-ink-900">
                  {locale === "ar" ? activeProgram.program_name_ar : activeProgram.program_name_en}
                </h3>
                <p className="text-xs text-ink-500">{c.evidenceSubtitle}</p>
              </div>
              <button
                type="button"
                onClick={() => setActiveProgram(null)}
                className="rounded-lg p-1.5 text-ink-400 hover:bg-slate-100 hover:text-ink-600"
              >
                ✕
              </button>
            </div>

            {/* Modal Rules Content */}
            <div className="overflow-y-auto p-5 space-y-4">
              {activeProgram.rules.map((rule: FundingProgramRule) => (
                <div
                  key={rule.id}
                  className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 text-xs space-y-2"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-bold text-ink-900">
                      {rule.rule_key}
                    </span>
                    <span className="rounded-md bg-indigo-50 px-2 py-0.5 font-medium text-indigo-700">
                      {rule.rule_type}
                    </span>
                  </div>

                  <p className="text-ink-700 leading-relaxed font-medium">
                    {locale === "ar" ? rule.description_ar : rule.description_en || rule.description_ar}
                  </p>

                  {/* Structured rule data */}
                  <div className="rounded-md bg-white border border-slate-100 p-2 text-[11px] font-mono text-ink-600">
                    {JSON.stringify(rule.structured_value, null, 2)}
                  </div>

                  {/* Provenance Metadata */}
                  <div className="grid grid-cols-1 gap-1.5 pt-2 border-t border-slate-100 text-[11px] text-ink-600 sm:grid-cols-2">
                    <div>
                      <span className="font-semibold text-ink-700">{c.sourceReference}:</span>{" "}
                      {rule.source_reference || "—"}
                    </div>
                    <div>
                      <span className="font-semibold text-ink-700">{c.sourceAuthority}:</span>{" "}
                      {rule.source_authority}
                    </div>
                    <div className="sm:col-span-2">
                      <span className="font-semibold text-ink-700">{c.sourceUrl}:</span>{" "}
                      <a
                        href={rule.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-brand-600 hover:underline break-all"
                      >
                        {rule.source_url}
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between border-t border-slate-100 p-4 bg-slate-50/50 rounded-b-2xl">
              <span className="text-[11px] text-ink-500">
                {locale === "ar"
                  ? "جميع القواعد خاضعة للتحقق والتحديث الدوري ومستندة للوائح الرسمية."
                  : "All rules subject to periodic verification based on official regulations."}
              </span>
              <button
                type="button"
                onClick={() => setActiveProgram(null)}
                className="rounded-lg bg-ink-900 px-4 py-1.5 text-xs font-medium text-white hover:bg-ink-800"
              >
                {c.close}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
