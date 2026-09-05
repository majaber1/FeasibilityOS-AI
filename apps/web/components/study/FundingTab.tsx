"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createAssumption,
  getBorrowingCapacity,
  getCollateralSummary,
  getFinancialHealth,
  getFinancingStructure,
  getFundingGap,
  getFundingMatches,
  getFundingReadiness,
  listFinancialPeriods,
  saveFinancialPeriod,
  type BorrowingCapacity,
  type CollateralSummary,
  type CompanyFinancialPeriod,
  type FinancialHealth,
  type FinancialPeriodUpdate,
  type FinancingStructure,
  type FundingGap,
  type FundingMatchesSummary,
  type FundingReadiness,
  type HealthMetric,
} from "@/lib/api";
import CollateralSection from "@/components/study/CollateralSection";
import FundingReadinessSection from "@/components/study/FundingReadinessSection";
import FundingMatchesSection from "@/components/study/FundingMatchesSection";
import FinancingStructureSection from "@/components/study/FinancingStructureSection";
import VerifiedFundingProgramsSection from "@/components/study/VerifiedFundingProgramsSection";

const copy = {
  ar: {
    title: "مركز التمويل والذكاء المالي",
    badgeWave: "Wave 2 — Funding Intelligence",
    badgeStatus: "فحص داخلي استرشادي",
    intro:
      "منظومة متكاملة لتقييم الجاهزية التمويلية، فحص فجوة رأس المال، قياس الطاقة الائتمانية الآمنة، تسجيل وتوثيق الضمانات، ومطابقة برامج الدعم والتمويل التنموي المعتمدة في المملكة العربية السعودية.",
    disclaimer:
      "⚠️ إخلاء مسؤولية تنظيمي معتمد: نتائج ومؤشرات مركز التمويل مخصصة للفحص الأولي الداخلي الاسترشادي (Internal Screening)، ولا تمثل موافقة ائتمانية ملزمة أو التزاماً بالتمويل من أي جهة حكومية أو مصرف تجاري أو صندوق تنموي. الموافقة النهائية خاضعة للدراسة الائتمانية الرسمية لدى الممول.",
    kpi: {
      readiness: "جاهزية التمويل",
      confirmedGap: "فجوة التمويل المؤكدة",
      screeningCapacity: "الطاقة الائتمانية للفحص",
      collateral: "الضمانات الموثّقة",
      matchedPrograms: "البرامج المطابقة",
      residualGap: "الفجوة المتبقية المحتملة",
      requirementSub: "الاحتياج الإجمالي",
      safeSub: "فحص آمن غير ملزم للبنوك",
      reportedSub: "من إجمالي مُبلَّغ",
      potentialSub: "بعد التمويل المحتمل",
      programsEvaluatedSub: "برنامج معتمد",
    },
    nav: {
      overview: "نظرة عامة",
      readiness: "الجاهزية",
      gap: "فجوة واحتياج التمويل",
      capacity: "القدرة التمويلية",
      collateral: "الضمانات",
      programs: "البرامج المعتمدة",
      matches: "مطابقة البرامج",
      structure: "هيكل التمويل",
      actions: "الخطوات القادمة",
    },
    quickActions: {
      heading: "إجراءات سريعة لملف التمويل",
      updateOwner: "تعديل مساهمة المالك",
      addCollateral: "إضافة / إدارة الضمانات",
      viewMatches: "فحص مطابقة البرامج",
      viewStructure: "استعراض هيكل التمويل",
      viewRoadmap: "خارطة الخطوات التالية",
      refresh: "تحديث بيانات المركز",
      refreshing: "جارٍ التحديث...",
    },
    readinessStatusLabels: {
      READY: "جاهز للتقديم",
      PARTIALLY_READY: "جاهز جزئياً",
      NEEDS_INFORMATION: "يلزم استكمال بيانات",
      NOT_READY: "غير جاهز حالياً",
    } as Record<string, string>,
    financialData: "البيانات المالية للشركة",
    financialDataSub: "القوائم المالية والافتراضات المدخلة لتقدير الطاقة الائتمانية والصحة المالية.",
    addPeriod: "إضافة/تحديث فترة مالية",
    periodLabel: "الفترة (مثال FY2025)",
    save: "حفظ",
    saving: "جارٍ الحفظ...",
    savedPeriods: "الفترات المحفوظة",
    noPeriods: "لا توجد بيانات مالية محفوظة بعد. أضف فترة مالية لبدء تحليل التمويل.",
    health: "الصحة المالية",
    healthEmpty: "لا يمكن حساب الصحة المالية بعد. أضف بيانات الفترة المالية أعلاه.",
    fundingGap: "احتياج وفجوة التمويل (Funding Need & Gap)",
    fundingGapIntro: "تحديد الاحتياج الرأسمالي الإجمالي، مساهمة المالك، والتسهيلات القائمة لحساب فجوة التمويل المؤكدة.",
    requirement: "احتياج المشروع",
    ownerCapital: "رأس مال المالك",
    facilities: "التسهيلات المتاحة",
    gap: "فجوة التمويل",
    quickSetOwner: "تحديد رأس مال المالك (ر.س)",
    quickSetFacilities: "تحديد التسهيلات المتاحة (ر.س)",
    set: "تحديد",
    capacity: "القدرة التمويلية التقديرية (Borrowing Capacity)",
    capacityIntro: "تقدير أولي آمن لسقف الاقتراض الممكن بناءً على التدفقات النقدية ومعايير الفحص الائتماني الداخلي.",
    capacityEmpty: "لا يمكن تقدير القدرة التمويلية بعد. أدخل البيانات المالية لحساب القدرة الآمنة.",
    missing: "بيانات ناقصة",
    baseCapacity: "القدرة الأساسية الآمنة",
    stressCapacity: "القدرة في السيناريو الضاغط",
    primaryConstraint: "المحدد الرئيسي",
    secondaryConstraint: "المحدد الثانوي",
    financialSupport: "مستوى الدعم المالي",
    underwritingMissing: "متطلبات تحقق ائتماني إضافية قبل التمويل الفعلي",
    toggleFinancialDetailsShow: "عرض تفاصيل القوائم والصحة المالية",
    toggleFinancialDetailsHide: "إخفاء تفاصيل القوائم والصحة المالية",
    sar: "ر.س",
    statusLabels: {
      CALCULATED: "محسوبة",
      MISSING_DATA: "بيانات ناقصة",
      NOT_APPLICABLE: "غير قابل للتطبيق",
    } as Record<string, string>,
    sourceLabels: {
      financial_statement: "قوائم مالية",
      bank_statement: "كشف بنكي",
      user_confirmed: "مؤكد من المستخدم",
      audited_statement: "قوائم مدققة",
      management_account: "حسابات إدارية",
      unverified: "غير موثّق",
    } as Record<string, string>,
  },
  en: {
    title: "Funding Intelligence Center",
    badgeWave: "Wave 2 — Funding Intelligence",
    badgeStatus: "Internal Screening Estimate",
    intro:
      "A consolidated platform to evaluate funding readiness, quantify funding need, measure safe borrowing capacity, manage verified collateral, and match verified Saudi development funding programs.",
    disclaimer:
      "⚠️ Regulatory Disclaimer: All estimates and screening results are strictly for internal screening guidance. They do not constitute an official credit approval or financing commitment from any governmental entity, bank, or development fund.",
    kpi: {
      readiness: "Funding Readiness",
      confirmedGap: "Confirmed Funding Gap",
      screeningCapacity: "Internal Screening Debt Capacity",
      collateral: "Verified Collateral",
      matchedPrograms: "Matched Programs",
      residualGap: "Potential Residual Gap",
      requirementSub: "Total Project Cost",
      safeSub: "Internal safe screening debt",
      reportedSub: "Of total reported",
      potentialSub: "After potential programs",
      programsEvaluatedSub: "Verified programs evaluated",
    },
    nav: {
      overview: "Overview",
      readiness: "Readiness",
      gap: "Funding Need",
      capacity: "Borrowing Capacity",
      collateral: "Collateral",
      programs: "Verified Programs",
      matches: "Funding Matches",
      structure: "Financing Structure",
      actions: "Next Actions",
    },
    quickActions: {
      heading: "Quick Funding Actions",
      updateOwner: "Update Owner Contribution",
      addCollateral: "Add / Manage Collateral",
      viewMatches: "Check Program Matches",
      viewStructure: "Review Financing Structure",
      viewRoadmap: "Next Actions Roadmap",
      refresh: "Refresh Center Data",
      refreshing: "Refreshing...",
    },
    readinessStatusLabels: {
      READY: "Ready to Approach Funders",
      PARTIALLY_READY: "Partially Ready",
      NEEDS_INFORMATION: "Needs Information",
      NOT_READY: "Not Ready Currently",
    } as Record<string, string>,
    financialData: "Company Financial Data",
    financialDataSub: "Financial statements and assumptions used to calculate borrowing capacity and financial health.",
    addPeriod: "Add / update a financial period",
    periodLabel: "Period (e.g. FY2025)",
    save: "Save",
    saving: "Saving...",
    savedPeriods: "Saved periods",
    noPeriods: "No financial data saved yet. Add a financial period to start the funding analysis.",
    health: "Financial Health",
    healthEmpty: "Financial health cannot be calculated yet. Add financial period data above.",
    fundingGap: "Funding Need & Gap",
    fundingGapIntro: "Quantify total project requirements, owner capital contribution, and available facilities to determine the confirmed funding gap.",
    requirement: "Project requirement",
    ownerCapital: "Owner capital",
    facilities: "Available facilities",
    gap: "Funding gap",
    quickSetOwner: "Set owner contribution (SAR)",
    quickSetFacilities: "Set available facilities (SAR)",
    set: "Set",
    capacity: "Estimated Borrowing Capacity",
    capacityIntro: "Safe preliminary screening cap for debt financing based on real cash flows and internal credit screening rules.",
    capacityEmpty: "Borrowing capacity cannot be estimated yet. Enter financial data above.",
    missing: "Missing data",
    baseCapacity: "Safe Base Capacity",
    stressCapacity: "Stress-case capacity",
    primaryConstraint: "Primary constraint",
    secondaryConstraint: "Secondary constraint",
    financialSupport: "Financial support",
    underwritingMissing: "Additional validation required before real financing",
    toggleFinancialDetailsShow: "Show Financial Statements & Health Metrics",
    toggleFinancialDetailsHide: "Hide Financial Statements & Health Metrics",
    sar: "SAR",
    statusLabels: {
      CALCULATED: "Calculated",
      MISSING_DATA: "Missing data",
      NOT_APPLICABLE: "Not applicable",
    } as Record<string, string>,
    sourceLabels: {
      financial_statement: "Financial statement",
      bank_statement: "Bank statement",
      user_confirmed: "User confirmed",
      audited_statement: "Audited statement",
      management_account: "Management account",
      unverified: "Unverified",
    } as Record<string, string>,
  },
};

const METRIC_ORDER = [
  "revenue_growth",
  "gross_margin",
  "ebitda_margin",
  "operating_margin",
  "net_margin",
  "working_capital",
  "current_ratio",
  "quick_ratio",
  "debt_to_equity",
  "debt_to_ebitda",
  "interest_coverage",
  "dscr",
];

const SUMMARY_ORDER = ["profitability", "liquidity", "leverage", "debt_service_capacity", "data_coverage"];

const SUMMARY_LABELS = {
  ar: {
    profitability: "الربحية",
    liquidity: "السيولة",
    leverage: "الرافعة المالية",
    debt_service_capacity: "قدرة خدمة الدين",
    data_coverage: "تغطية البيانات",
  },
  en: {
    profitability: "Profitability",
    liquidity: "Liquidity",
    leverage: "Leverage",
    debt_service_capacity: "Debt service capacity",
    data_coverage: "Data coverage",
  },
} as const;

const STATUS_STYLE: Record<string, string> = {
  CALCULATED: "bg-emerald-50 text-emerald-800",
  MISSING_DATA: "bg-amber-50 text-amber-800",
  NOT_APPLICABLE: "bg-slate-100 text-slate-600",
};

const SUMMARY_STYLE: Record<string, string> = {
  STRONG: "bg-emerald-50 text-emerald-800 border-emerald-200",
  ACCEPTABLE: "bg-sky-50 text-sky-800 border-sky-200",
  LOW: "bg-emerald-50 text-emerald-800 border-emerald-200",
  MODERATE: "bg-sky-50 text-sky-800 border-sky-200",
  WEAK: "bg-red-50 text-red-700 border-red-200",
  HIGH: "bg-red-50 text-red-700 border-red-200",
  FULL: "bg-emerald-50 text-emerald-800 border-emerald-200",
  PARTIAL: "bg-amber-50 text-amber-800 border-amber-200",
  MINIMAL: "bg-red-50 text-red-700 border-red-200",
  INSUFFICIENT_DATA: "bg-slate-100 text-slate-600 border-slate-200",
};

const READINESS_BADGE_STYLE: Record<string, string> = {
  READY: "bg-emerald-100 text-emerald-800 border-emerald-300",
  PARTIALLY_READY: "bg-amber-100 text-amber-800 border-amber-300",
  NEEDS_INFORMATION: "bg-sky-100 text-sky-800 border-sky-300",
  NOT_READY: "bg-rose-100 text-rose-800 border-rose-300",
};

const FIELD_KEYS: (keyof FinancialPeriodUpdate)[] = [
  "revenue",
  "gross_profit",
  "ebitda",
  "operating_profit",
  "net_profit",
  "cash",
  "current_assets",
  "current_liabilities",
  "total_assets",
  "total_liabilities",
  "equity",
  "existing_debt",
  "annual_debt_service",
  "interest_expense",
  "accounts_receivable",
  "inventory",
  "capital_expenditure",
];

function fmt(n: number | null | undefined, locale: "ar" | "en") {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-SA", { maximumFractionDigits: 0 }).format(n);
}

type Props = { token: string; studyId: number; locale: "ar" | "en" };

const emptyForm: Record<string, string> = Object.fromEntries(FIELD_KEYS.map((k) => [k, ""]));

export default function FundingTab({ token, studyId, locale }: Props) {
  const c = copy[locale];

  // Core Wave 2 Data State
  const [periods, setPeriods] = useState<CompanyFinancialPeriod[] | null>(null);
  const [health, setHealth] = useState<FinancialHealth | null | undefined>(undefined);
  const [gap, setGap] = useState<FundingGap | null>(null);
  const [capacity, setCapacity] = useState<BorrowingCapacity | null | undefined>(undefined);
  const [readiness, setReadiness] = useState<FundingReadiness | null>(null);
  const [collateralSummary, setCollateralSummary] = useState<CollateralSummary | null>(null);
  const [matchesSummary, setMatchesSummary] = useState<FundingMatchesSummary | null>(null);
  const [financingStructure, setFinancingStructure] = useState<FinancingStructure | null>(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Financial Period Form State
  const [periodLabel, setPeriodLabel] = useState("FY2025");
  const [source, setSource] = useState("user_confirmed");
  const [form, setForm] = useState<Record<string, string>>(emptyForm);
  const [busy, setBusy] = useState(false);

  // Funding Need Assumption State
  const [ownerInput, setOwnerInput] = useState("");
  const [facilitiesInput, setFacilitiesInput] = useState("");
  const [assumptionBusy, setAssumptionBusy] = useState<"owner" | "facilities" | null>(null);

  // Navigation & Progressive Disclosure State
  const [activeNav, setActiveNav] = useState<string>("funding-overview");
  const [showFinancialDetails, setShowFinancialDetails] = useState<boolean>(false);

  // Cascading Refresh Signal for Children
  const [refreshSignal, setRefreshSignal] = useState(0);

  const reload = useCallback(async () => {
    try {
      setError(null);
      const [
        periodRows,
        healthRow,
        gapRow,
        capacityRow,
        readinessRow,
        collateralRow,
        matchesRow,
        structureRow,
      ] = await Promise.all([
        listFinancialPeriods(token, studyId).catch(() => null),
        getFinancialHealth(token, studyId).catch(() => null),
        getFundingGap(token, studyId).catch(() => null),
        getBorrowingCapacity(token, studyId).catch(() => null),
        getFundingReadiness(token, studyId).catch(() => null),
        getCollateralSummary(token, studyId).catch(() => null),
        getFundingMatches(token, studyId).catch(() => null),
        getFinancingStructure(token, studyId).catch(() => null),
      ]);

      setPeriods(periodRows);
      setHealth(healthRow);
      setGap(gapRow);
      setCapacity(capacityRow);
      setReadiness(readinessRow);
      setCollateralSummary(collateralRow);
      setMatchesSummary(matchesRow);
      setFinancingStructure(structureRow);

      setRefreshSignal((prev) => prev + 1);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, studyId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleManualRefresh = async () => {
    setRefreshing(true);
    await reload();
  };

  const scrollTo = (targetId: string) => {
    setActiveNav(targetId);
    const el = document.getElementById(targetId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  async function onSavePeriod(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload: FinancialPeriodUpdate = { source: source as FinancialPeriodUpdate["source"] };
      for (const key of FIELD_KEYS) {
        const raw = form[key];
        if (raw !== "" && raw !== undefined) (payload as Record<string, number>)[key] = Number(raw);
      }
      await saveFinancialPeriod(token, studyId, periodLabel, payload);
      setForm(emptyForm);
      await reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  async function onSetAssumption(kind: "owner" | "facilities") {
    const value = kind === "owner" ? ownerInput : facilitiesInput;
    if (!value) return;
    setAssumptionBusy(kind);
    setError(null);
    try {
      const key = kind === "owner" ? "owner_contribution" : "existing_available_facilities";
      await createAssumption(token, studyId, {
        key,
        label_en: kind === "owner" ? "Owner contribution" : "Existing available facilities",
        label_ar: kind === "owner" ? "رأس مال المالك" : "التسهيلات المتاحة",
        value_number: Number(value),
        unit: "SAR",
        origin: "USER",
      });
      if (kind === "owner") setOwnerInput("");
      else setFacilitiesInput("");
      await reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setAssumptionBusy(null);
    }
  }

  // Navigation Items
  const navItems = [
    { id: "funding-overview", label: c.nav.overview, icon: "📊" },
    { id: "funding-readiness-section", label: c.nav.readiness, icon: "🎯" },
    { id: "funding-gap", label: c.nav.gap, icon: "💰" },
    { id: "borrowing-capacity", label: c.nav.capacity, icon: "📈" },
    { id: "collateral-section", label: c.nav.collateral, icon: "🛡️" },
    { id: "verified-funding-programs", label: c.nav.programs, icon: "🏛️" },
    { id: "funding-matches-section", label: c.nav.matches, icon: "⚡" },
    { id: "financing-structure-section", label: c.nav.structure, icon: "⚖️" },
    { id: "next-actions-section", label: c.nav.actions, icon: "📋" },
  ];

  // Derived KPI values strictly from live APIs
  const confirmedGapVal = financingStructure?.confirmed_funding_gap ?? gap?.funding_gap ?? 0;
  const safeDebtVal = capacity?.status === "CALCULATED"
    ? (financingStructure?.internal_screening_debt_capacity ?? capacity.base_capacity)
    : null;
  const verifiedCollateralVal = collateralSummary?.total_verified_value ?? 0;
  const potentialResidualVal = financingStructure?.potential_residual_gap ?? 0;

  return (
    <div className="mt-5 space-y-10">
      {/* 1. FUNDING OVERVIEW SECTION */}
      <section
        id="funding-overview"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-6"
      >
        {/* Header Title & Badges */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex h-3 w-3 rounded-full bg-brand-600 ring-4 ring-brand-100 animate-pulse" />
              <span className="rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-semibold text-brand-700 border border-brand-200">
                {c.badgeWave}
              </span>
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                {c.badgeStatus}
              </span>
            </div>
            <h2 className="mt-2 text-2xl font-bold text-ink-900">{c.title}</h2>
            <p className="mt-1.5 max-w-4xl text-sm text-ink-600 leading-relaxed">{c.intro}</p>
          </div>

          <button
            type="button"
            onClick={handleManualRefresh}
            disabled={refreshing}
            className="self-start md:self-auto inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-slate-50 px-3.5 py-2 text-xs font-semibold text-ink-700 hover:bg-slate-100 transition shadow-sm disabled:opacity-60"
          >
            <span className={`text-sm ${refreshing ? "animate-spin" : ""}`}>🔄</span>
            <span>{refreshing ? c.quickActions.refreshing : c.quickActions.refresh}</span>
          </button>
        </div>

        {/* Regulatory Disclaimer */}
        <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 text-xs font-medium text-amber-900 leading-relaxed">
          {c.disclaimer}
        </div>

        {error && (
          <div role="alert" className="rounded-xl bg-red-50 border border-red-200 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* 6 Real Live KPI Cards */}
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-500 mb-3">
            {locale === "ar" ? "مؤشرات مركز التمويل الأساسية" : "Key Funding Center Metrics"}
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
            {/* KPI 1: Funding Readiness */}
            <article className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 hover:border-brand-300 transition">
              <p className="text-xs font-medium text-ink-500">{c.kpi.readiness}</p>
              <div className="mt-2">
                {readiness ? (
                  <span
                    className={`inline-block rounded-md border px-2 py-1 text-xs font-bold ${
                      READINESS_BADGE_STYLE[readiness.status] ?? "bg-slate-100 text-slate-800"
                    }`}
                  >
                    {c.readinessStatusLabels[readiness.status] ?? readiness.status}
                  </span>
                ) : (
                  <p className="text-sm font-semibold text-ink-400">—</p>
                )}
              </div>
              <p className="mt-2 text-[10px] text-ink-400">
                {readiness ? (locale === "ar" ? "فحص المعايير الداخلية" : "Internal screening") : "—"}
              </p>
            </article>

            {/* KPI 2: Confirmed Funding Gap */}
            <article className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 hover:border-brand-300 transition">
              <p className="text-xs font-medium text-ink-500">{c.kpi.confirmedGap}</p>
              <p className="mt-2 text-base font-bold text-ink-900">
                {fmt(confirmedGapVal, locale)} <span className="text-xs font-normal">{c.sar}</span>
              </p>
              <p className="mt-2 text-[10px] text-ink-500">
                {c.kpi.requirementSub}: {fmt(gap?.total_project_requirement ?? financingStructure?.total_project_requirement, locale)} {c.sar}
              </p>
            </article>

            {/* KPI 3: Internal Screening Debt Capacity */}
            <article className="flex flex-col justify-between rounded-xl border border-emerald-200 bg-emerald-50/40 p-3.5 hover:border-emerald-300 transition">
              <p className="text-xs font-medium text-emerald-800">{c.kpi.screeningCapacity}</p>
              <p className="mt-2 text-base font-bold text-emerald-950">
                {fmt(safeDebtVal, locale)} <span className="text-xs font-normal">{c.sar}</span>
              </p>
              <p className="mt-2 text-[10px] text-emerald-700">{c.kpi.safeSub}</p>
            </article>

            {/* KPI 4: Verified Collateral */}
            <article className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 hover:border-brand-300 transition">
              <p className="text-xs font-medium text-ink-500">{c.kpi.collateral}</p>
              <p className="mt-2 text-base font-bold text-ink-900">
                {fmt(verifiedCollateralVal, locale)} <span className="text-xs font-normal">{c.sar}</span>
              </p>
              <p className="mt-2 text-[10px] text-ink-500">
                {c.kpi.reportedSub}: {fmt(collateralSummary?.total_reported_value ?? 0, locale)} {c.sar}
              </p>
            </article>

            {/* KPI 5: Matched Programs */}
            <article className="flex flex-col justify-between rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 hover:border-brand-300 transition">
              <p className="text-xs font-medium text-ink-500">{c.kpi.matchedPrograms}</p>
              <div className="mt-2">
                <span className="text-base font-bold text-brand-700">
                  {matchesSummary?.matches_count ?? 0}
                </span>
                {matchesSummary && matchesSummary.possible_matches_count > 0 && (
                  <span className="text-xs font-medium text-amber-700 mx-1">
                    (+{matchesSummary.possible_matches_count} {locale === "ar" ? "محتمل" : "poss."})
                  </span>
                )}
              </div>
              <p className="mt-2 text-[10px] text-ink-500">
                {matchesSummary ? `${matchesSummary.total_programs_evaluated} ${c.kpi.programsEvaluatedSub}` : "—"}
              </p>
            </article>

            {/* KPI 6: Potential Residual Gap */}
            <article className="flex flex-col justify-between rounded-xl border border-indigo-200 bg-indigo-50/40 p-3.5 hover:border-indigo-300 transition">
              <p className="text-xs font-medium text-indigo-900">{c.kpi.residualGap}</p>
              <p className="mt-2 text-base font-bold text-indigo-950">
                {fmt(potentialResidualVal, locale)} <span className="text-xs font-normal">{c.sar}</span>
              </p>
              <p className="mt-2 text-[10px] text-indigo-700">{c.kpi.potentialSub}</p>
            </article>
          </div>
        </div>

        {/* Quick Action Shortcuts */}
        <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-ink-600 mr-1">{c.quickActions.heading}:</span>
          <button
            type="button"
            onClick={() => scrollTo("funding-gap")}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-ink-700 hover:bg-slate-100 transition"
          >
            <span>✏️</span>
            <span>{c.quickActions.updateOwner}</span>
          </button>
          <button
            type="button"
            onClick={() => scrollTo("collateral-section")}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-ink-700 hover:bg-slate-100 transition"
          >
            <span>🛡️</span>
            <span>{c.quickActions.addCollateral}</span>
          </button>
          <button
            type="button"
            onClick={() => scrollTo("funding-matches-section")}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-ink-700 hover:bg-slate-100 transition"
          >
            <span>⚡</span>
            <span>{c.quickActions.viewMatches}</span>
          </button>
          <button
            type="button"
            onClick={() => scrollTo("financing-structure-section")}
            className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-ink-700 hover:bg-slate-100 transition"
          >
            <span>⚖️</span>
            <span>{c.quickActions.viewStructure}</span>
          </button>
          <button
            type="button"
            onClick={() => scrollTo("next-actions-section")}
            className="inline-flex items-center gap-1 rounded-lg border border-brand-200 bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-800 hover:bg-brand-100 transition"
          >
            <span>📋</span>
            <span>{c.quickActions.viewRoadmap}</span>
          </button>
        </div>
      </section>

      {/* STICKY FUNDING CENTER SUB-NAVIGATION */}
      <nav
        aria-label="Funding Center Navigation"
        className="sticky top-2 z-20 flex items-center gap-1.5 overflow-x-auto rounded-2xl border border-slate-200 bg-white/95 p-2 backdrop-blur-md shadow-md no-scrollbar"
      >
        {navItems.map((item) => {
          const isActive = activeNav === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => scrollTo(item.id)}
              className={`shrink-0 inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                isActive
                  ? "bg-brand-600 text-white shadow-sm"
                  : "bg-slate-50 text-ink-700 hover:bg-slate-100 hover:text-ink-900 border border-slate-200/60"
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* 2. FINANCIAL READINESS */}
      <FundingReadinessSection readiness={readiness} locale={locale} loading={loading} />

      {/* 3. FUNDING NEED */}
      <section id="funding-gap" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm">💰</span>
            <h3 className="text-xl font-bold text-ink-900">{c.fundingGap}</h3>
          </div>
          <p className="mt-1 text-sm text-ink-600 leading-relaxed">{c.fundingGapIntro}</p>
        </div>

        {gap === null ? (
          <div className="py-6 text-center text-sm text-ink-500 animate-pulse">…</div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-4">
            <article className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <p className="text-xs font-medium text-ink-500">{c.requirement}</p>
              <p className="mt-1.5 text-lg font-bold text-ink-900">
                {fmt(gap.total_project_requirement, locale)} {c.sar}
              </p>
            </article>

            <article className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <p className="text-xs font-medium text-ink-500">{c.ownerCapital}</p>
              <p className="mt-1.5 text-lg font-bold text-ink-900">
                {fmt(gap.owner_available_capital, locale)} {c.sar}
              </p>
              {gap.owner_available_capital_status === "MISSING_DATA" && (
                <span className="inline-block mt-1 text-[11px] font-semibold text-amber-700">
                  {c.statusLabels.MISSING_DATA}
                </span>
              )}
            </article>

            <article className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
              <p className="text-xs font-medium text-ink-500">{c.facilities}</p>
              <p className="mt-1.5 text-lg font-bold text-ink-900">
                {fmt(gap.existing_available_facilities, locale)} {c.sar}
              </p>
              {gap.existing_available_facilities_status === "MISSING_DATA" && (
                <span className="inline-block mt-1 text-[11px] font-semibold text-amber-700">
                  {c.statusLabels.MISSING_DATA}
                </span>
              )}
            </article>

            <article className="rounded-xl border border-brand-200 bg-brand-50/60 p-4">
              <p className="text-xs font-medium text-brand-700">{c.gap}</p>
              <p className="mt-1.5 text-lg font-bold text-brand-900">
                {fmt(gap.funding_gap, locale)} {c.sar}
              </p>
            </article>
          </div>
        )}

        {/* Controlled Inputs for Updating Owner Contribution & Facilities */}
        <div className="grid gap-4 sm:grid-cols-2 pt-3 border-t border-slate-100">
          <div className="flex gap-2">
            <input
              type="number"
              placeholder={c.quickSetOwner}
              value={ownerInput}
              onChange={(e) => setOwnerInput(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-sm text-ink-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => onSetAssumption("owner")}
              disabled={assumptionBusy === "owner"}
              className="shrink-0 rounded-xl border border-brand-500 bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-100 transition disabled:opacity-60"
            >
              {assumptionBusy === "owner" ? "..." : c.set}
            </button>
          </div>

          <div className="flex gap-2">
            <input
              type="number"
              placeholder={c.quickSetFacilities}
              value={facilitiesInput}
              onChange={(e) => setFacilitiesInput(e.target.value)}
              className="w-full rounded-xl border border-slate-300 px-3.5 py-2 text-sm text-ink-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none"
            />
            <button
              type="button"
              onClick={() => onSetAssumption("facilities")}
              disabled={assumptionBusy === "facilities"}
              className="shrink-0 rounded-xl border border-brand-500 bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-100 transition disabled:opacity-60"
            >
              {assumptionBusy === "facilities" ? "..." : c.set}
            </button>
          </div>
        </div>
      </section>

      {/* 4. BORROWING CAPACITY & FINANCIAL PROFILE */}
      <section
        id="borrowing-capacity"
        className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-6"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm">📈</span>
              <h3 className="text-xl font-bold text-ink-900">{c.capacity}</h3>
            </div>
            <p className="mt-1 text-sm text-ink-600 leading-relaxed">{c.capacityIntro}</p>
          </div>

          <button
            type="button"
            onClick={() => setShowFinancialDetails((prev) => !prev)}
            className="self-start sm:self-auto inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-semibold text-ink-700 hover:bg-slate-100 transition"
          >
            <span>{showFinancialDetails ? "▲" : "▼"}</span>
            <span>{showFinancialDetails ? c.toggleFinancialDetailsHide : c.toggleFinancialDetailsShow}</span>
          </button>
        </div>

        {capacity === undefined ? (
          <p className="text-sm text-ink-500 animate-pulse">…</p>
        ) : capacity === null || capacity.status === "INSUFFICIENT_DATA" ? (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-ink-600 space-y-2">
            <p className="font-semibold text-ink-800">{c.capacityEmpty}</p>
            {capacity?.missing_inputs && capacity.missing_inputs.length > 0 && (
              <p className="text-xs text-amber-800">
                <span className="font-bold">{c.missing}:</span> {capacity.missing_inputs.join(", ")}
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <article className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4">
                <p className="text-xs font-medium text-emerald-800">{c.baseCapacity}</p>
                <p className="mt-1.5 text-xl font-bold text-emerald-950">
                  {fmt(capacity.base_capacity, locale)} {c.sar}
                </p>
              </article>
              <article className="rounded-xl border border-amber-200 bg-amber-50/60 p-4">
                <p className="text-xs font-medium text-amber-800">{c.stressCapacity}</p>
                <p className="mt-1.5 text-xl font-bold text-amber-950">
                  {fmt(capacity.stress_capacity, locale)} {c.sar}
                </p>
              </article>
            </div>

            <div className="grid gap-2 sm:grid-cols-2 text-xs">
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                <span className="font-semibold text-ink-700">{c.primaryConstraint}: </span>
                <span className="text-ink-900">{capacity.primary_constraint}</span>
              </div>
              {capacity.secondary_constraint && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5">
                  <span className="font-semibold text-ink-700">{c.secondaryConstraint}: </span>
                  <span className="text-ink-900">{capacity.secondary_constraint}</span>
                </div>
              )}
              <div className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 flex items-center justify-between sm:col-span-2">
                <span className="font-semibold text-ink-700">{c.financialSupport}: </span>
                <span
                  className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                    SUMMARY_STYLE[capacity.financial_support] ?? ""
                  }`}
                >
                  {capacity.financial_support}
                </span>
              </div>
            </div>

            {capacity.missing_inputs.length > 0 && (
              <p className="text-xs text-amber-800">
                <span className="font-bold">{c.missing}:</span> {capacity.missing_inputs.join(", ")}
              </p>
            )}

            {capacity.missing_underwriting_inputs && capacity.missing_underwriting_inputs.length > 0 && (
              <div className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 text-xs text-ink-600 space-y-1.5">
                <p className="font-bold text-ink-800">{c.underwritingMissing}:</p>
                <ul className="list-inside list-disc space-y-1 text-ink-700">
                  {capacity.missing_underwriting_inputs.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}

            <p className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs font-medium text-amber-900 leading-relaxed">
              {capacity.disclaimer}
            </p>
          </div>
        )}

        {/* Expandable Company Financial Data & Financial Health */}
        {showFinancialDetails && (
          <div className="space-y-6 pt-5 border-t border-slate-200">
            {/* Company Financial Data Section */}
            <section id="company-financial-data" className="space-y-4">
              <div>
                <h4 className="font-bold text-ink-900 text-base">{c.financialData}</h4>
                <p className="text-xs text-ink-500 mt-0.5">{c.financialDataSub}</p>
              </div>

              {periods === null ? (
                <p className="text-xs text-ink-500 animate-pulse">…</p>
              ) : periods.length === 0 ? (
                <p className="text-xs text-ink-500">{c.noPeriods}</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {periods.map((p) => (
                    <span
                      key={p.id}
                      className="rounded-full bg-slate-100 border border-slate-200 px-3 py-1 text-xs font-medium text-ink-700"
                    >
                      {p.period} · {c.sourceLabels[p.source]} · {fmt(p.revenue, locale)}{" "}
                      {locale === "ar" ? "ر.س إيراد" : "SAR revenue"}
                    </span>
                  ))}
                </div>
              )}

              <form
                onSubmit={onSavePeriod}
                className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4 sm:grid-cols-3"
              >
                <h5 className="text-xs font-bold text-ink-800 sm:col-span-3">{c.addPeriod}</h5>
                <label className="block text-xs font-medium text-ink-700">
                  <span>{c.periodLabel}</span>
                  <input
                    value={periodLabel}
                    onChange={(e) => setPeriodLabel(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-ink-900 focus:border-brand-500 focus:outline-none"
                  />
                </label>
                <label className="block text-xs font-medium text-ink-700 sm:col-span-2">
                  <span>{locale === "ar" ? "مصدر البيانات" : "Data source"}</span>
                  <select
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-ink-900 focus:border-brand-500 focus:outline-none"
                  >
                    {Object.entries(c.sourceLabels).map(([val, lbl]) => (
                      <option key={val} value={val}>
                        {lbl}
                      </option>
                    ))}
                  </select>
                </label>
                {FIELD_KEYS.map((key) => (
                  <label key={key} className="block text-xs font-medium text-ink-700">
                    <span className="capitalize">{key.replace(/_/g, " ")}</span>
                    <input
                      type="number"
                      value={form[key]}
                      onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-ink-900 focus:border-brand-500 focus:outline-none"
                    />
                  </label>
                ))}
                <div className="sm:col-span-3 flex justify-end">
                  <button
                    type="submit"
                    disabled={busy}
                    className="rounded-xl bg-brand-600 px-4 py-2 text-xs font-semibold text-white hover:bg-brand-700 transition disabled:opacity-60"
                  >
                    {busy ? c.saving : c.save}
                  </button>
                </div>
              </form>
            </section>

            {/* Financial Health Section */}
            <section id="financial-health" className="space-y-4 pt-4 border-t border-slate-200">
              <h4 className="font-bold text-ink-900 text-base">{c.health}</h4>
              {health === undefined ? (
                <p className="text-xs text-ink-500 animate-pulse">…</p>
              ) : health === null ? (
                <p className="text-xs text-ink-500">{c.healthEmpty}</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-2">
                    {SUMMARY_ORDER.map((key) => (
                      <span
                        key={key}
                        className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                          SUMMARY_STYLE[health.summary[key]] ?? ""
                        }`}
                      >
                        {SUMMARY_LABELS[locale][key as keyof (typeof SUMMARY_LABELS)["ar"]]}: {health.summary[key]}
                      </span>
                    ))}
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {METRIC_ORDER.filter((k) => health.metrics[k]).map((key) => {
                      const m: HealthMetric = health.metrics[key];
                      return (
                        <div
                          key={key}
                          className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-2.5 text-xs"
                        >
                          <span className="capitalize text-ink-600">{key.replace(/_/g, " ")}</span>
                          <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLE[m.status]}`}>
                            {m.status === "CALCULATED"
                              ? `${fmt(m.value, locale)}${m.unit === "percent" ? "%" : ""}`
                              : c.statusLabels[m.status]}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </section>
          </div>
        )}
      </section>

      {/* 5. COLLATERAL */}
      <CollateralSection token={token} studyId={studyId} locale={locale} onChanged={reload} />

      {/* 6. VERIFIED PROGRAMS */}
      <VerifiedFundingProgramsSection token={token} locale={locale} />

      {/* 7. FUNDING MATCHES */}
      <FundingMatchesSection token={token} studyId={studyId} refreshSignal={refreshSignal} />

      {/* 8. FINANCING STRUCTURE (includes #next-actions-section) */}
      <FinancingStructureSection token={token} studyId={studyId} refreshSignal={refreshSignal} />
    </div>
  );
}
