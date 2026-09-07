"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import {
  listVerifiedOpportunities,
  getVerifiedOpportunity,
  compareVerifiedOpportunities,
  createStudyFromOpportunity,
  getOpportunityFitProfile,
  saveOpportunityFitProfile,
  evaluateOpportunityFit,
  getOpportunityFitResults,
  getToken,
  type VerifiedOpportunity,
  type OpportunityComparisonItem,
  type FitProfile,
  type OpportunityMatchItem,
  type MatchRunResponse,
} from "@/lib/api";

const SECTOR_OPTIONS = [
  { value: "", label_ar: "جميع القطاعات", label_en: "All Sectors" },
  { value: "food_beverage", label_ar: "أغذية ومشروبات ومقاهي", label_en: "Food & Beverage / Coffee" },
  { value: "manufacturing", label_ar: "صناعات تحويلية وتعبئة", label_en: "Manufacturing & Packaging" },
  { value: "logistics", label_ar: "خدمات لوجستية وتخزين مبرد", label_en: "Logistics & Cold Storage" },
  { value: "agriculture", label_ar: "زراعة وتقنيات مائية حديثة", label_en: "Agriculture & Agritech" },
  { value: "industrial", label_ar: "صناعة وتدوير بيئي", label_en: "Industrial & Recycling" },
  { value: "sports_entertainment", label_ar: "رياضة وترفيه ولياقة", label_en: "Sports & Fitness" },
  { value: "retail", label_ar: "تجزئة ورعاية متخصصة", label_en: "Specialty Retail" },
  { value: "services", label_ar: "خدمات وبنية تحتية مشتركة", label_en: "Services & Shared Infra" },
];

const GEOGRAPHY_OPTIONS = [
  { value: "", label_ar: "جميع المناطق", label_en: "All Regions" },
  { value: "KSA_NATIONAL", label_ar: "تغطية وطنية شاملة", label_en: "KSA Nationwide" },
  { value: "RIYADH", label_ar: "منطقة الرياض", label_en: "Riyadh Region" },
  { value: "WESTERN", label_ar: "المنطقة الغربية (مكة / جدة)", label_en: "Western Region" },
  { value: "EASTERN", label_ar: "المنطقة الشرقية", label_en: "Eastern Region" },
  { value: "QASSIM", label_ar: "منطقة القصيم", label_en: "Al-Qassim Region" },
];

function fmtSAR(n: number | null | undefined, locale: "ar" | "en") {
  if (n === null || n === undefined) return locale === "ar" ? "غير معلن" : "Unspecified";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n) + (locale === "ar" ? " ر.س" : " SAR");
}

export default function OpportunitiesPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const router = useRouter();

  // Active view tab
  const [activeTab, setActiveTab] = useState<"all" | "BUSINESS_OPPORTUNITY" | "FRANCHISE" | "compare" | "my-fit">("all");

  // Registry filter states
  const [sector, setSector] = useState("");
  const [geography, setGeography] = useState("");
  const [budget, setBudget] = useState<string>("");
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<VerifiedOpportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const parsedBudget = parseFloat(budget);
  const hasBudget = !Number.isNaN(parsedBudget) && parsedBudget > 0;
  const budgetFitItems = useMemo(
    () => (hasBudget ? items.filter((o) => o.investment_min !== null && o.investment_min !== undefined && o.investment_min <= parsedBudget) : []),
    [hasBudget, items, parsedBudget]
  );
  const budgetUnknownItems = useMemo(
    () => (hasBudget ? items.filter((o) => o.investment_min === null || o.investment_min === undefined) : []),
    [hasBudget, items]
  );

  // Selection for comparison (max 4)
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [comparisonItems, setComparisonItems] = useState<OpportunityComparisonItem[]>([]);
  const [comparisonLoading, setComparisonLoading] = useState(false);

  // Detail Modal state
  const [detailItem, setDetailItem] = useState<VerifiedOpportunity | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Create Study Modal state
  const [targetForStudy, setTargetForStudy] = useState<VerifiedOpportunity | null>(null);
  const [studyTitle, setStudyTitle] = useState("");
  const [customBudget, setCustomBudget] = useState<string>("");
  const [creatingStudy, setCreatingStudy] = useState(false);
  const [createStudyError, setCreateStudyError] = useState("");
  const [studyMatchResultId, setStudyMatchResultId] = useState<number | undefined>(undefined);

  // Fit & Matching states (Wave 3B) - Neutral defaults for new users
  const [fitProfile, setFitProfile] = useState<FitProfile>({
    available_capital: null,
    capital_constraint_type: "HARD",
    preferred_sectors: [],
    excluded_sectors: [],
    preferred_opportunity_types: [],
    opportunity_type_constraint: "PREFERENCE",
    target_region: null,
    target_city: null,
    preferred_business_models: [],
    target_customer: null,
    experience_sectors: [],
    notes: "",
  });
  const [matchRun, setMatchRun] = useState<MatchRunResponse | null>(null);
  const [evaluatingFit, setEvaluatingFit] = useState(false);
  const [fitLoading, setFitLoading] = useState(false);
  const [fitError, setFitError] = useState("");
  const [selectedMatchForExplain, setSelectedMatchForExplain] = useState<OpportunityMatchItem | null>(null);

  // Fetch opportunities matching current filters
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");

    const filterType = activeTab === "all" || activeTab === "compare" || activeTab === "my-fit" ? undefined : activeTab;

    listVerifiedOpportunities({
      type: filterType,
      sector: sector || undefined,
      geography: geography || undefined,
      search: search.trim() || undefined,
    })
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeTab, sector, geography, budget, search]);

  // Fetch Fit Profile and Latest Match Run if authenticated
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    setFitLoading(true);

    Promise.all([
      getOpportunityFitProfile(token).catch(() => null),
      getOpportunityFitResults(token).catch(() => null),
    ])
      .then(([prof, run]) => {
        if (prof) {
          setFitProfile((prev) => ({
            ...prev,
            ...prof,
            available_capital: prof.available_capital !== undefined ? prof.available_capital : prev.available_capital,
            preferred_sectors: prof.preferred_sectors ?? [],
            excluded_sectors: prof.excluded_sectors ?? [],
            preferred_opportunity_types: prof.preferred_opportunity_types ?? [],
            preferred_business_models: prof.preferred_business_models ?? [],
            target_customer: prof.target_customer ?? null,
            experience_sectors: prof.experience_sectors ?? [],
            target_region: prof.target_region ?? null,
            target_city: prof.target_city ?? null,
            notes: prof.notes ?? "",
          }));
        }
        if (run) {
          setMatchRun(run);
        }
      })
      .finally(() => {
        setFitLoading(false);
      });
  }, []);

  // Load comparison data when compare tab is opened or selectedIds change
  useEffect(() => {
    if (activeTab === "compare" && selectedIds.length > 0) {
      setComparisonLoading(true);
      compareVerifiedOpportunities(selectedIds)
        .then(setComparisonItems)
        .catch(() => setComparisonItems([]))
        .finally(() => setComparisonLoading(false));
    }
  }, [activeTab, selectedIds]);

  // Comparison toggle
  const toggleComparison = (id: number) => {
    setSelectedIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      if (prev.length >= 4) {
        alert(ar ? "يمكنك مقارنة 4 فرص كحد أقصى في وقت واحد" : "You can compare up to 4 opportunities simultaneously");
        return prev;
      }
      return [...prev, id];
    });
  };

  // Open detail view
  const openDetail = async (id: number) => {
    setDetailLoading(true);
    try {
      const data = await getVerifiedOpportunity(id);
      setDetailItem(data);
    } catch {
      const fallback = items.find((i) => i.id === id);
      if (fallback) setDetailItem(fallback);
    } finally {
      setDetailLoading(false);
    }
  };

  // Prepare create study modal
  const openCreateStudy = (opp: VerifiedOpportunity, matchResultId?: number) => {
    const token = getToken();
    if (!token) {
      router.push(`/login?next=${encodeURIComponent("/opportunities")}`);
      return;
    }
    setTargetForStudy(opp);
    setStudyMatchResultId(matchResultId);
    setStudyTitle(ar ? (opp.brand_name ? `دراسة امتياز: ${opp.brand_name}` : `دراسة: ${opp.title_ar}`) : `Study: ${opp.title_en}`);
    // If investment is unannounced in source, pre-fill with investor available capital or empty
    if (opp.investment_min) {
      setCustomBudget(String(opp.investment_min));
    } else if (fitProfile.available_capital && fitProfile.available_capital > 0) {
      setCustomBudget(String(fitProfile.available_capital));
    } else {
      setCustomBudget("");
    }
    setCreateStudyError("");
  };

  // Execute create study
  const handleConfirmCreateStudy = async () => {
    if (!targetForStudy) return;
    const token = getToken();
    if (!token) {
      router.push(`/login?next=${encodeURIComponent("/opportunities")}`);
      return;
    }

    const parsedBudget = parseFloat(customBudget);
    if (!targetForStudy.investment_min && (Number.isNaN(parsedBudget) || parsedBudget <= 0)) {
      setCreateStudyError(
        ar
          ? "الميزانية الرأسمالية غير معلنة في المصدر الرسمي للفرصة. يرجى إدخال الميزانية المقترحة (كافتراض مستخدم صريح) لبدء الدراسة."
          : "Investment budget is unannounced in the official source. Please specify a proposed budget as an explicit user assumption."
      );
      return;
    }

    setCreatingStudy(true);
    setCreateStudyError("");

    try {
      const res = await createStudyFromOpportunity(token, targetForStudy.id, {
        study_title: studyTitle.trim() || undefined,
        custom_budget: !Number.isNaN(parsedBudget) && parsedBudget > 0 ? parsedBudget : undefined,
        match_result_id: studyMatchResultId,
      });

      router.push(`/projects/${res.project_id}/studies/${res.study_id}`);
    } catch (err) {
      setCreateStudyError(err instanceof Error ? err.message : String(err));
      setCreatingStudy(false);
    }
  };

  // Save profile and trigger evaluation
  const handleEvaluateFit = async () => {
    const token = getToken();
    if (!token) {
      router.push(`/login?next=${encodeURIComponent("/opportunities")}`);
      return;
    }

    setEvaluatingFit(true);
    setFitError("");

    try {
      // 1. Save profile
      await saveOpportunityFitProfile(token, fitProfile);
      // 2. Evaluate fit
      const run = await evaluateOpportunityFit(token);
      setMatchRun(run);
    } catch (err) {
      setFitError(err instanceof Error ? err.message : String(err));
    } finally {
      setEvaluatingFit(false);
    }
  };

  const getMatchStateBadge = (state: string) => {
    switch (state) {
      case "MATCH":
        return {
          bg: "bg-emerald-100 text-emerald-800 border-emerald-300",
          text_ar: "تطابق تام (MATCH)",
          text_en: "Verified Fit (MATCH)",
        };
      case "POSSIBLE_MATCH":
        return {
          bg: "bg-amber-100 text-amber-800 border-amber-300",
          text_ar: "تطابق محتمل (POSSIBLE_MATCH)",
          text_en: "Possible Fit (POSSIBLE_MATCH)",
        };
      case "NEEDS_INFORMATION":
        return {
          bg: "bg-blue-100 text-blue-800 border-blue-300",
          text_ar: "يتطلب معلومات إضافية (NEEDS_INFORMATION)",
          text_en: "Needs Info (NEEDS_INFORMATION)",
        };
      case "NOT_MATCHED":
        return {
          bg: "bg-rose-100 text-rose-800 border-rose-300",
          text_ar: "غير متطابق مع القيود (NOT_MATCHED)",
          text_en: "Not Matched (NOT_MATCHED)",
        };
      case "NOT_EVALUATED":
      default:
        return {
          bg: "bg-slate-100 text-slate-700 border-slate-300",
          text_ar: "غير خاضعة للتقييم (NOT_EVALUATED)",
          text_en: "Not Evaluated (NOT_EVALUATED)",
        };
    }
  };

  const renderCard = (opp: VerifiedOpportunity) => {
    const isCompared = selectedIds.includes(opp.id);
    const isFranchise = opp.opportunity_type === "FRANCHISE";

    return (
      <div
        key={opp.id}
        data-testid="opportunity-card"
        className="flex flex-col justify-between rounded-3xl border border-slate-200/80 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
      >
        <div>
          {/* Badges */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                isFranchise ? "bg-purple-100 text-purple-800" : "bg-emerald-100 text-emerald-800"
              }`}
            >
              {isFranchise ? (ar ? "امتياز تجاري" : "Franchise") : (ar ? "فرصة استثمارية" : "Business Opp")}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
              {opp.verification_status}
            </span>
          </div>

          {/* Title & Brand */}
          <h3 data-testid="opportunity-card-title" className="mt-3 text-base font-bold text-slate-900">
            {ar ? opp.title_ar : opp.title_en}
          </h3>
          {opp.brand_name && (
            <p className="mt-0.5 text-xs font-semibold text-brand-700">{opp.brand_name}</p>
          )}
          <p className="mt-1 text-xs text-slate-500">
            {opp.sector} {opp.city ? `· ${opp.city}` : ""}
          </p>

          {/* Description excerpt */}
          <p className="mt-3 line-clamp-3 text-xs leading-relaxed text-slate-600">
            {ar ? opp.description_ar : opp.description_en}
          </p>

          {/* Financial and Requirements Facts */}
          <div className="mt-5 space-y-2 rounded-2xl bg-slate-50/80 p-3.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">{ar ? "الاستثمار التقديري:" : "Est. Investment:"}</span>
              <span className="font-mono font-medium text-slate-900">
                {opp.investment_min
                  ? `${fmtSAR(opp.investment_min, locale)} – ${fmtSAR(opp.investment_max, locale)}`
                  : (ar ? "غير معلن - يحدده المستثمر" : "Unannounced (Investor Assumption)")}
              </span>
            </div>

            {isFranchise && (
              <div className="flex items-center justify-between">
                <span className="text-slate-500">{ar ? "رسوم الامتياز:" : "Franchise Fee:"}</span>
                <span className="font-mono font-medium text-slate-900">
                  {opp.franchise_fee !== null && opp.franchise_fee !== undefined
                    ? fmtSAR(opp.franchise_fee, locale)
                    : (ar ? "غير معلنة في البوابة العامة" : "Unannounced in Public Portal")}
                </span>
              </div>
            )}

            <div className="flex items-center justify-between">
              <span className="text-slate-500">{ar ? "النطاق الجغرافي:" : "Geography:"}</span>
              <span className="font-medium text-slate-700">
                {opp.city ? `${opp.city} (${opp.region || ""})` : (ar ? "تغطية وطنية شاملة" : "Nationwide KSA")}
              </span>
            </div>

            <div className="flex items-center justify-between border-t border-slate-200/60 pt-2">
              <span className="text-slate-500">{ar ? "المصدر المعتمد:" : "Source:"}</span>
              <a
                href={opp.official_source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 font-medium text-brand-700 hover:underline"
              >
                <span>{opp.source_owner}</span>
                <span className="text-[10px]">↗</span>
              </a>
            </div>
          </div>
        </div>

        {/* Card Actions */}
        <div className="mt-6 flex flex-col gap-2 pt-2">
          <div className="flex items-center gap-2">
            <button
              onClick={() => openDetail(opp.id)}
              className="flex-1 rounded-xl border border-slate-200 bg-white py-2 text-center text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              {ar ? "عرض التفاصيل والأدلة" : "View Evidence"}
            </button>
            <button
              onClick={() => toggleComparison(opp.id)}
              className={`rounded-xl border px-3 py-2 text-xs font-medium transition ${
                isCompared
                  ? "border-brand-600 bg-brand-50 text-brand-700"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {isCompared ? (ar ? "✓ مضاف للمقارنة" : "✓ Added") : (ar ? "+ إضافة للمقارنة" : "+ Compare")}
            </button>
          </div>

          <button
            onClick={() => openCreateStudy(opp)}
            className="w-full rounded-xl bg-brand-600 py-2.5 text-center text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700"
          >
            {ar ? "بدء دراسة الجدوى من هذه الفرصة" : "Start Feasibility Study"}
          </button>
        </div>
      </div>
    );
  };

  return (
    <main className="min-h-screen bg-slate-50/50 py-8">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
            <div>
              <div className="flex items-center gap-2">
                <span className="rounded-md bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-700">
                  {ar ? "سجل الفرص والامتياز المعتمد" : "Verified Opportunities Registry"}
                </span>
                <span className="rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
                  {ar ? "أدلة موثقة 100%" : "100% Source Backed"}
                </span>
              </div>
              <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                {ar ? "الفرص الاستثمارية والامتياز التجاري المعتمد" : "Verified Opportunities & Franchise Hub"}
              </h1>
              <p className="mt-2 max-w-3xl text-xs leading-relaxed text-slate-600 sm:text-sm">
                {ar
                  ? "بوابة استكشاف ومطابقة الفرص الاستثمارية وحزم الامتياز التجاري في المملكة العربية السعودية، مبنية على وثائق الجهات الرسمية المنشورة دون أرقام مفبركة أو نقاط ترجيح اصطناعية."
                  : "Explore verified business and franchise opportunities across Saudi Arabia backed by authoritative official sources without synthetic scores."}
              </p>
            </div>

            {/* Quick Actions / Compare summary */}
            {selectedIds.length > 0 && (
              <div className="flex items-center gap-3 rounded-2xl border border-brand-200 bg-brand-50/50 p-3">
                <div className="text-xs text-brand-900">
                  <span className="font-bold">{selectedIds.length}</span> {ar ? "فرص محددة" : "selected"}
                </div>
                <button
                  onClick={() => setActiveTab("compare")}
                  className="rounded-xl bg-brand-600 px-4 py-2 text-xs font-semibold text-white shadow hover:bg-brand-700"
                >
                  {ar ? "فتح جدول المقارنة" : "View Comparison"}
                </button>
                <button
                  onClick={() => setSelectedIds([])}
                  className="text-xs text-slate-500 hover:text-slate-800"
                >
                  {ar ? "إلغاء" : "Clear"}
                </button>
              </div>
            )}
          </div>

          {/* Official Provenance Authorities Banner */}
          <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4 text-xs text-slate-500">
            <span className="font-medium text-slate-700">{ar ? "الجهات المرجعية الرسمية:" : "Official Source Authorities:"}</span>
            <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-slate-700">الهيئة العامة للمنشآت (منشآت)</span>
            <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-slate-700">استثمر في السعودية (وزارة الاستثمار)</span>
            <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-slate-700">مركز الامتياز التجاري السعودي</span>
            <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-slate-700">صندوق التنمية الزراعية (ADF)</span>
            <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-slate-700">المركز الوطني لإدارة النفايات (موان)</span>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="mt-6 flex flex-wrap items-center gap-2 border-b border-slate-200 pb-2">
          <button
            onClick={() => setActiveTab("all")}
            className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
              activeTab === "all" ? "bg-slate-900 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-slate-100"
            }`}
          >
            {ar ? "جميع الفرص والامتياز" : "All Opportunities"}
          </button>
          <button
            onClick={() => setActiveTab("BUSINESS_OPPORTUNITY")}
            className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
              activeTab === "BUSINESS_OPPORTUNITY" ? "bg-slate-900 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-slate-100"
            }`}
          >
            {ar ? "الفرص التجارية والصناعية" : "Business Opportunities"}
          </button>
          <button
            onClick={() => setActiveTab("FRANCHISE")}
            className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
              activeTab === "FRANCHISE" ? "bg-slate-900 text-white shadow-sm" : "bg-white text-slate-600 hover:bg-slate-100"
            }`}
          >
            {ar ? "فرص الامتياز التجاري (الفرانشايز)" : "Franchise Brands"}
          </button>
          <button
            data-testid="my-fit-tab"
            onClick={() => setActiveTab("my-fit")}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${
              activeTab === "my-fit" ? "bg-brand-600 text-white shadow-sm" : "bg-brand-50 text-brand-900 hover:bg-brand-100"
            }`}
          >
            <span>🎯</span>
            <span>{ar ? "فرص تناسبني (My Fit)" : "My Fit & Matching"}</span>
          </button>
          {selectedIds.length > 0 && (
            <button
              onClick={() => setActiveTab("compare")}
              className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                activeTab === "compare" ? "bg-purple-700 text-white shadow-sm" : "bg-purple-50 text-purple-800 hover:bg-purple-100"
              }`}
            >
              {ar ? `المقارنة المباشرة (${selectedIds.length})` : `Side-by-side Compare (${selectedIds.length})`}
            </button>
          )}
        </div>

        {/* MY FIT TAB (WAVE 3B) */}
        {activeTab === "my-fit" ? (
          <div className="mt-6 space-y-6">
            {/* Fit Profile Setup Form */}
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
              <div className="border-b border-slate-100 pb-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-bold text-slate-900">
                      {ar ? "أهدافي وقيودي الاستثمارية (Investor Profile & Constraints)" : "Investor Fit Profile & Constraints"}
                    </h2>
                    <p className="mt-1 text-xs text-slate-500">
                      {ar
                        ? "حدد رأس المال المتاح والقطاعات المستهدفة والمستبعدة لتحديد الفرص المتوافقة معك بدقة وحتمية دون نسب مئوية وهمية."
                        : "Define your capital, preferred sectors, and hard exclusions for deterministic fit matching."}
                    </p>
                  </div>
                  {fitProfile.version && (
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-mono text-slate-600">
                      {ar ? `إصدار الملف: v${fitProfile.version}` : `Profile v${fitProfile.version}`}
                    </span>
                  )}
                </div>
              </div>

              <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {/* Available Capital */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "رأس المال المتاح للاستثمار (ر.س)" : "Available Capital (SAR)"}
                  </label>
                  <input
                    data-testid="capital-input"
                    type="number"
                    min={0}
                    step={10000}
                    value={fitProfile.available_capital ?? ""}
                    onChange={(e) =>
                      setFitProfile({
                        ...fitProfile,
                        available_capital: e.target.value ? parseFloat(e.target.value) : null,
                      })
                    }
                    placeholder="450,000"
                    className="mt-1.5 w-full rounded-xl border border-slate-300 p-2.5 font-mono text-xs outline-none focus:border-brand-500"
                  />
                  <p className="mt-1 text-[11px] text-slate-400">
                    {ar ? "يُعامل كقيد مقارنة مع الحد الأدنى المنشور رسميّاً" : "Compared against published minimum"}
                  </p>
                </div>

                {/* Capital Constraint Type */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "طبيعة قيد رأس المال" : "Capital Constraint Strictness"}
                  </label>
                  <select
                    data-testid="capital-strength-select"
                    value={fitProfile.capital_constraint_type ?? "HARD"}
                    onChange={(e) => setFitProfile({ ...fitProfile, capital_constraint_type: e.target.value as "HARD" | "PREFERENCE" })}
                    className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white p-2.5 text-xs outline-none focus:border-brand-500"
                  >
                    <option value="HARD">{ar ? "قيد حتمي — لا أتجاوز رأس المال" : "Strict Hard Limit (No Overrun)"}</option>
                    <option value="PREFERENCE">{ar ? "تفضيل — يمكنني مراجعة خيارات أعلى من الميزانية" : "Preference (Review Options Above Budget)"}</option>
                  </select>
                </div>

                {/* Preferred Sectors */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "القطاع المفضل الرئيسي" : "Primary Preferred Sector"}
                  </label>
                  <select
                    data-testid="preferred-sectors-select"
                    value={fitProfile.preferred_sectors?.[0] ?? ""}
                    onChange={(e) =>
                      setFitProfile({
                        ...fitProfile,
                        preferred_sectors: e.target.value ? [e.target.value] : [],
                      })
                    }
                    className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white p-2.5 text-xs outline-none focus:border-brand-500"
                  >
                    {SECTOR_OPTIONS.map((s) => (
                      <option key={s.value} value={s.value}>
                        {ar ? s.label_ar : s.label_en}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Excluded Sectors (Hard Failure) */}
                <div>
                  <label className="block text-xs font-semibold text-rose-700">
                    {ar ? "قطاعات مستبعدة تماماً (قيد حتمي مستبعد)" : "Excluded Sectors (Hard Exclusion)"}
                  </label>
                  <select
                    data-testid="excluded-sectors-select"
                    value={fitProfile.excluded_sectors?.[0] ?? ""}
                    onChange={(e) =>
                      setFitProfile({
                        ...fitProfile,
                        excluded_sectors: e.target.value ? [e.target.value] : [],
                      })
                    }
                    className="mt-1.5 w-full rounded-xl border border-rose-300 bg-white p-2.5 text-xs outline-none focus:border-rose-500"
                  >
                    <option value="">{ar ? "لا يوجد قطاع مستبعد" : "None (No Exclusions)"}</option>
                    {SECTOR_OPTIONS.filter((s) => s.value).map((s) => (
                      <option key={s.value} value={s.value}>
                        {ar ? s.label_ar : s.label_en}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-[11px] text-rose-500">
                    {ar ? "أي فرصة في هذا القطاع سيتم استبعادها كـ NOT_MATCHED" : "Opportunities here become NOT_MATCHED"}
                  </p>
                </div>

                {/* Preferred Opportunity Type */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "نوع الفرصة المفضل" : "Preferred Opportunity Type"}
                  </label>
                  <select
                    data-testid="opp-type-select"
                    value={fitProfile.preferred_opportunity_types?.[0] ?? ""}
                    onChange={(e) =>
                      setFitProfile({
                        ...fitProfile,
                        preferred_opportunity_types: e.target.value ? [e.target.value] : [],
                      })
                    }
                    className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white p-2.5 text-xs outline-none focus:border-brand-500"
                  >
                    <option value="">{ar ? "الكل / بدون تفضيل محدد" : "All / No Preference"}</option>
                    <option value="FRANCHISE">{ar ? "امتياز تجاري (FRANCHISE)" : "Franchise"}</option>
                    <option value="BUSINESS_OPPORTUNITY">{ar ? "فرصة مستقلة (BUSINESS_OPPORTUNITY)" : "Business Opportunity"}</option>
                  </select>
                </div>

                {/* Target Customer */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "نوع العميل المستهدف" : "Target Customer"}
                  </label>
                  <select
                    data-testid="target-customer-select"
                    value={fitProfile.target_customer ?? ""}
                    onChange={(e) =>
                      setFitProfile({
                        ...fitProfile,
                        target_customer: e.target.value || null,
                      })
                    }
                    className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white p-2.5 text-xs outline-none focus:border-brand-500"
                  >
                    <option value="">{ar ? "الكل / بدون تفضيل محدد" : "All / No Preference"}</option>
                    <option value="B2C">{ar ? "أفراد ومستهلكين (B2C)" : "Consumers (B2C)"}</option>
                    <option value="B2B">{ar ? "منشآت وشركات (B2B)" : "Businesses (B2B)"}</option>
                  </select>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {ar ? "تفضيل استرشادي يحدد درجة التوافق" : "Preference factor for fit alignment"}
                  </p>
                </div>

                {/* Preferred Business Model */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "نموذج العمل المفضل" : "Preferred Business Model"}
                  </label>
                  <input
                    data-testid="business-model-input"
                    type="text"
                    value={fitProfile.preferred_business_models?.[0] ?? ""}
                    onChange={(e) =>
                      setFitProfile({
                        ...fitProfile,
                        preferred_business_models: e.target.value.trim() ? [e.target.value.trim()] : [],
                      })
                    }
                    placeholder={ar ? "مثال: Franchise Branch أو Drive-Thru أو Wholesale" : "e.g. Franchise Branch, Drive-Thru"}
                    className="mt-1.5 w-full rounded-xl border border-slate-300 p-2.5 text-xs outline-none focus:border-brand-500"
                  />
                  <p className="mt-1 text-[11px] text-slate-400">
                    {ar ? "تفضيل تشغيلي غير مستبعد حتمياً" : "Non-critical operational preference"}
                  </p>
                </div>

                {/* Experience Sector */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "قطاع الخبرة السابقة للمستثمر" : "Investor Experience Sector"}
                  </label>
                  <select
                    data-testid="experience-sectors-select"
                    value={fitProfile.experience_sectors?.[0] ?? ""}
                    onChange={(e) =>
                      setFitProfile({
                        ...fitProfile,
                        experience_sectors: e.target.value ? [e.target.value] : [],
                      })
                    }
                    className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white p-2.5 text-xs outline-none focus:border-brand-500"
                  >
                    <option value="">{ar ? "لا توجد خبرة محددة" : "No specific sector experience"}</option>
                    {SECTOR_OPTIONS.filter((s) => s.value).map((s) => (
                      <option key={s.value} value={s.value}>
                        {ar ? s.label_ar : s.label_en}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {ar ? "عامل تفضيل ولا يؤدي لاستبعاد الفرص" : "Preference factor; never excludes opportunities"}
                  </p>
                </div>

                {/* Target Region */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "المنطقة المستهدفة" : "Target Region"}
                  </label>
                  <input
                    data-testid="target-region-input"
                    type="text"
                    value={fitProfile.target_region ?? ""}
                    onChange={(e) => setFitProfile({ ...fitProfile, target_region: e.target.value })}
                    placeholder={ar ? "مثال: الرياض أو KSA_NATIONAL" : "e.g. Riyadh Region"}
                    className="mt-1.5 w-full rounded-xl border border-slate-300 p-2.5 text-xs outline-none focus:border-brand-500"
                  />
                </div>

                {/* Target City */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "المدينة المستهدفة" : "Target City"}
                  </label>
                  <input
                    data-testid="target-city-input"
                    type="text"
                    value={fitProfile.target_city ?? ""}
                    onChange={(e) => setFitProfile({ ...fitProfile, target_city: e.target.value })}
                    placeholder={ar ? "مثال: الرياض / جدة" : "e.g. Riyadh / Jeddah"}
                    className="mt-1.5 w-full rounded-xl border border-slate-300 p-2.5 text-xs outline-none focus:border-brand-500"
                  />
                </div>

                {/* Notes */}
                <div className="sm:col-span-2 lg:col-span-3">
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "ملاحظات إضافية وتفضيلات استثمارية" : "Additional Investor Notes"}
                  </label>
                  <input
                    data-testid="fit-notes-input"
                    type="text"
                    value={fitProfile.notes ?? ""}
                    onChange={(e) => setFitProfile({ ...fitProfile, notes: e.target.value })}
                    placeholder={ar ? "سجل أي اعتبارات خاصة ترغب بأخذها في الحسبان" : "Any special notes..."}
                    className="mt-1.5 w-full rounded-xl border border-slate-300 p-2.5 text-xs outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              {fitError && (
                <p role="alert" className="mt-4 rounded-xl bg-red-50 p-3 text-xs text-red-700">
                  {fitError}
                </p>
              )}

              <div className="mt-6 flex items-center justify-end gap-3 border-t border-slate-100 pt-4">
                <button
                  data-testid="evaluate-fit-btn"
                  onClick={handleEvaluateFit}
                  disabled={evaluatingFit}
                  className="flex items-center gap-2 rounded-xl bg-brand-600 px-6 py-2.5 text-xs font-semibold text-white shadow hover:bg-brand-700 disabled:opacity-50"
                >
                  <span>⚡</span>
                  <span>{evaluatingFit ? (ar ? "جارٍ تقييم المطابقة..." : "Evaluating Fit...") : (ar ? "حفظ وتشغيل المطابقة الحتمية" : "Save & Run Deterministic Fit")}</span>
                </button>
              </div>
            </div>

            {/* Match Run Results Section */}
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
              <div className="flex flex-col justify-between gap-2 border-b border-slate-100 pb-4 sm:flex-row sm:items-center">
                <div>
                  <h3 className="text-lg font-bold text-slate-900">
                    {ar ? "نتائج مطابقة الفرص المعتمدة" : "Verified Opportunities Match Results"}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    {ar
                      ? "المطابقة تتم وفق قواعد حتمية واضحة وموثقة دون أرقام أو احتمالات اصطناعية."
                      : "Deterministic criteria evaluation without artificial weights or synthetic scores."}
                  </p>
                </div>
                {matchRun && (
                  <div className="text-xs text-slate-500">
                    {ar ? `تم التقييم: ${matchRun.evaluated_at ? new Date(matchRun.evaluated_at).toLocaleTimeString() : ""}` : `Evaluated: ${matchRun.evaluated_at ?? ""}`}
                  </div>
                )}
              </div>

              {!matchRun ? (
                <div className="py-16 text-center text-sm text-slate-500">
                  {fitLoading ? (
                    <span>{ar ? "جارٍ تحميل الملف والمطابقة..." : "Loading profile..."}</span>
                  ) : (
                    <div>
                      <p>{ar ? "لم يتم تشغيل المطابقة بعد. اضغط على زر 'حفظ وتشغيل المطابقة' أعلاه لعرض الفرص المتوافقة مع أهدافك." : "Click 'Save & Run Deterministic Fit' above to evaluate opportunities."}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {matchRun.results.map((item) => {
                    const badge = getMatchStateBadge(item.match_state);
                    const originalOpp = items.find((o) => o.id === item.opportunity_id);

                    return (
                      <div
                        key={item.result_id}
                        data-testid="opportunity-card"
                        className="flex flex-col justify-between rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition hover:shadow-md"
                      >
                        <div>
                          {/* Match State Badge */}
                          <div className="flex items-center justify-between gap-2">
                            <span className={`rounded-full border px-3 py-1 text-xs font-bold ${badge.bg}`}>
                              {ar ? badge.text_ar : badge.text_en}
                            </span>
                            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
                              {item.verification_status}
                            </span>
                          </div>

                          {/* Title & Brand */}
                          <h4 data-testid="opportunity-card-title" className="mt-3 text-base font-bold text-slate-900">
                            {ar ? item.title_ar : item.title_en}
                          </h4>
                          {item.brand_name && (
                            <p className="mt-0.5 text-xs font-semibold text-brand-700">{item.brand_name}</p>
                          )}
                          <p className="mt-1 text-xs text-slate-500">
                            {item.sector} · {item.opportunity_type === "FRANCHISE" ? (ar ? "امتياز تجاري" : "Franchise") : (ar ? "فرصة تجارية" : "Business")}
                          </p>

                          {/* Summary Reason */}
                          <div className="mt-4 rounded-2xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
                            <span className="font-bold text-slate-900">{ar ? "تعليل المطابقة: " : "Evaluation Reason: "}</span>
                            <span>{item.summary_reason}</span>
                          </div>

                          {/* Missing Information Alerts (Wave 3B Integrity) */}
                          {item.missing_information && item.missing_information.length > 0 && (
                            <div className="mt-3 rounded-2xl bg-amber-50/70 p-3 text-xs text-amber-900">
                              <p className="font-bold text-amber-950">{ar ? "معلومات مطلوب استيفاؤها:" : "Missing Information:"}</p>
                              <ul className="mt-1 list-inside list-disc space-y-0.5 text-[11px]">
                                {item.missing_information.map((m, idx) => (
                                  <li key={idx}>{m}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Investment Facts */}
                          <div className="mt-4 space-y-1 rounded-2xl border border-slate-100 bg-slate-50/50 p-3 text-xs">
                            <div className="flex items-center justify-between">
                              <span className="text-slate-500">{ar ? "الاستثمار المطلوب المنشور:" : "Published Investment:"}</span>
                              <span className="font-mono font-medium text-slate-900">
                                {item.investment_min
                                  ? `${fmtSAR(item.investment_min, locale)} – ${fmtSAR(item.investment_max, locale)}`
                                  : (ar ? "غير معلن في المصدر الرسمي" : "Unannounced in Official Source")}
                              </span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-slate-500">{ar ? "رأس مالك المحدد:" : "Your Budget:"}</span>
                              <span className="font-mono font-medium text-brand-700">
                                {fmtSAR(matchRun.fit_profile_snapshot.available_capital, locale)}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="mt-6 flex flex-col gap-2 pt-2">
                          <button
                            data-testid="explain-fit-btn"
                            onClick={() => setSelectedMatchForExplain(item)}
                            className="w-full rounded-xl border border-slate-300 bg-white py-2 text-center text-xs font-semibold text-slate-800 transition hover:bg-slate-50"
                          >
                            {ar ? "🔍 شرح الملاءمة التفصيلي (Explain Fit)" : "🔍 Explain Fit Details"}
                          </button>

                          {item.match_state !== "NOT_EVALUATED" ? (
                            <button
                              data-testid="start-study-btn"
                              onClick={() => {
                                if (originalOpp) {
                                  openCreateStudy(originalOpp, item.result_id);
                                } else {
                                  // Construct minimum object to launch study
                                  openCreateStudy(
                                    {
                                      id: item.opportunity_id,
                                      slug: item.slug,
                                      title_ar: item.title_ar,
                                      title_en: item.title_en,
                                      opportunity_type: item.opportunity_type === "BUSINESS_OPPORTUNITY" ? "BUSINESS_OPPORTUNITY" : "FRANCHISE",
                                      brand_name: item.brand_name,
                                      sector: item.sector,
                                      investment_min: item.investment_min ?? null,
                                      investment_max: item.investment_max ?? null,
                                      franchise_fee: item.franchise_fee ?? null,
                                      geography: item.geography || "KSA_NATIONAL",
                                      source_owner: "Official Verified Authority",
                                      source_type: "PRIMARY_PORTAL",
                                      official_source_url: item.official_source_url || "",
                                      verification_status: item.verification_status,
                                      is_active: item.is_active,
                                      data_version: String(item.opportunity_version_at_eval),
                                      first_seen_at: "",
                                      last_checked_at: "",
                                      last_verified_at: "",
                                    },
                                    item.result_id
                                  );
                                }
                              }}
                              className="w-full rounded-xl bg-brand-600 py-2.5 text-center text-xs font-semibold text-white shadow-sm transition hover:bg-brand-700"
                            >
                              {ar ? "بدء دراسة الجدوى مع نتائج المطابقة" : "Start Study with Fit Snapshot"}
                            </button>
                          ) : (
                            <div className="rounded-xl bg-slate-100 py-2 text-center text-[11px] font-medium text-slate-500">
                              {ar ? "غير متاح لبدء دراسة (سجل غير موثق)" : "Study disabled (Unverified)"}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        ) : activeTab === "compare" ? (
          /* Comparison View */
          <div className="mt-6 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">
                  {ar ? "المقارنة الموضوعية المباشرة" : "Factual Side-by-Side Comparison"}
                </h2>
                <p className="mt-1 text-xs text-slate-500">
                  {ar ? "مقارنة مبنية على الحقول الموثقة من المصدر الرسمي حصراً دون نقاط ترجيح اصطناعية" : "Strict comparison of verified source fields with zero artificial scoring"}
                </p>
              </div>
              <button
                onClick={() => setActiveTab("all")}
                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
              >
                {ar ? "العودة للقائمة" : "Back to List"}
              </button>
            </div>

            {comparisonLoading ? (
              <div className="py-16 text-center text-sm text-slate-500">{ar ? "جارٍ إعداد جدول المقارنة..." : "Loading comparison..."}</div>
            ) : comparisonItems.length === 0 ? (
              <div className="py-16 text-center text-sm text-slate-500">
                {ar ? "لم يتم تحديد أي فرص للمقارنة. حدد فرصة واحدة أو أكثر من القائمة." : "No opportunities selected for comparison."}
              </div>
            ) : (
              <div className="mt-6 overflow-x-auto">
                <table className="w-full border-collapse text-right text-xs sm:text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-slate-700">
                      <th className="p-3 font-semibold">{ar ? "المعيار" : "Attribute"}</th>
                      {comparisonItems.map((item) => (
                        <th key={item.id} className="min-w-[220px] p-3 font-semibold text-slate-900">
                          <div className="flex items-center justify-between gap-2">
                            <span>{ar ? item.title_ar : item.title_en}</span>
                            <button
                              onClick={() => toggleComparison(item.id)}
                              className="text-xs text-red-500 hover:underline"
                              title={ar ? "إزالة من المقارنة" : "Remove"}
                            >
                              ✕
                            </button>
                          </div>
                          {item.brand_name && (
                            <span className="mt-1 block text-xs font-normal text-brand-700">{item.brand_name}</span>
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {/* Match State Row (if match run exists) */}
                    {matchRun && (
                      <tr className="bg-brand-50/30">
                        <td className="p-3 font-bold text-brand-900">{ar ? "حالة المطابقة الحتمية" : "Deterministic Fit State"}</td>
                        {comparisonItems.map((i) => {
                          const m = matchRun.results.find((r) => r.opportunity_id === i.id);
                          const b = m ? getMatchStateBadge(m.match_state) : null;
                          return (
                            <td key={i.id} className="p-3">
                              {b ? (
                                <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-bold ${b.bg}`}>
                                  {ar ? b.text_ar : b.text_en}
                                </span>
                              ) : (
                                <span className="text-slate-400">—</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    )}
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "نوع الفرصة" : "Type"}</td>
                      {comparisonItems.map((i) => (
                        <td key={i.id} className="p-3 font-medium text-slate-800">
                          {i.opportunity_type === "FRANCHISE" ? (ar ? "امتياز تجاري" : "Franchise") : (ar ? "فرصة استثمارية" : "Business Opportunity")}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "القطاع" : "Sector"}</td>
                      {comparisonItems.map((i) => (
                        <td key={i.id} className="p-3 text-slate-700">{i.sector}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "النطاق الجغرافي" : "Geography"}</td>
                      {comparisonItems.map((i) => (
                        <td key={i.id} className="p-3 text-slate-700">
                          {i.city ? `${i.city} (${i.region || ""})` : (ar ? "تغطية وطنية شاملة" : "Nationwide")}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "نطاق الاستثمار المنشور" : "Published Investment"}</td>
                      {comparisonItems.map((i) => (
                        <td key={i.id} className="p-3 font-mono text-slate-800">
                          {fmtSAR(i.investment_min, locale)} – {fmtSAR(i.investment_max, locale)}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "رسوم الامتياز (الفرانشايز)" : "Franchise Fee"}</td>
                      {comparisonItems.map((i) => (
                        <td key={i.id} className="p-3 text-slate-700">
                          {i.franchise_fee ? fmtSAR(i.franchise_fee, locale) : (ar ? "غير منطبق / غير معلن" : "N/A")}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "نموذج الإتاوة والملكية" : "Royalty Model"}</td>
                      {comparisonItems.map((i) => (
                        <td key={i.id} className="p-3 text-xs text-slate-700">{i.royalty_model || "—"}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "المساحة التشغيلية المطلوبة" : "Required Space"}</td>
                      {comparisonItems.map((i) => (
                        <td key={i.id} className="p-3 text-slate-700">{i.required_space || "—"}</td>
                      ))}
                    </tr>
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "جهة المصدر الرسمي" : "Source Owner"}</td>
                      {comparisonItems.map((i) => (
                        <td key={i.id} className="p-3 text-xs text-slate-700">
                          <a
                            href={i.official_source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="font-medium text-brand-700 hover:underline"
                          >
                            {i.source_owner} ↗
                          </a>
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "حالة التوثيق" : "Verification Status"}</td>
                      {comparisonItems.map((i) => (
                        <td key={i.id} className="p-3">
                          <span className="inline-block rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
                            {i.verification_status}
                          </span>
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "حالة الملاءمة (Wave 3B)" : "Fit Status (Wave 3B)"}</td>
                      {comparisonItems.map((i) => {
                        const fit = matchRun?.results?.find((e: OpportunityMatchItem) => e.opportunity_id === i.id);
                        if (!fit) {
                          return (
                            <td key={i.id} className="p-3 text-xs text-slate-400">
                              {ar ? "لم يتم التقييم" : "Not Evaluated"}
                            </td>
                          );
                        }
                        const badge = getMatchStateBadge(fit.match_state);
                        return (
                          <td key={i.id} className="p-3">
                            <span className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-semibold ${badge.bg}`}>
                              {ar ? badge.text_ar : badge.text_en}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                    <tr>
                      <td className="bg-slate-50/50 p-3 font-medium text-slate-600">{ar ? "إجراء اتخاذ القرار" : "Action"}</td>
                      {comparisonItems.map((i) => {
                        const original = items.find((o) => o.id === i.id);
                        return (
                          <td key={i.id} className="p-3">
                            <button
                              onClick={() => {
                                if (original) openCreateStudy(original);
                              }}
                              className="w-full rounded-xl bg-brand-600 px-3 py-2 text-xs font-semibold text-white hover:bg-brand-700"
                            >
                              {ar ? "إنشاء دراسة جدوى" : "Create Study"}
                            </button>
                          </td>
                        );
                      })}
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          /* Normal List View */
          <>
            {/* Filters Bar */}
            <div className="mt-6 grid gap-4 rounded-3xl border border-slate-200/80 bg-white p-5 shadow-sm sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="block text-xs font-medium text-slate-700">{ar ? "القطاع الاستثماري" : "Sector"}</label>
                <select
                  value={sector}
                  onChange={(e) => setSector(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3 py-2 text-xs font-medium text-slate-800 outline-none focus:border-brand-500 focus:bg-white"
                >
                  {SECTOR_OPTIONS.map((s) => (
                    <option key={s.value} value={s.value}>
                      {ar ? s.label_ar : s.label_en}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">{ar ? "النطاق الجغرافي" : "Geography"}</label>
                <select
                  value={geography}
                  onChange={(e) => setGeography(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3 py-2 text-xs font-medium text-slate-800 outline-none focus:border-brand-500 focus:bg-white"
                >
                  {GEOGRAPHY_OPTIONS.map((g) => (
                    <option key={g.value} value={g.value}>
                      {ar ? g.label_ar : g.label_en}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">
                  {ar ? "الحد الأقصى للميزانية (ر.س)" : "Max Budget (SAR)"}
                </label>
                <input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  placeholder={ar ? "أدخل سقف ميزانيتك (مثال: 500,000)" : "e.g. 500,000"}
                  className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3 py-2 text-xs font-medium text-slate-800 outline-none focus:border-brand-500 focus:bg-white"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700">{ar ? "بحث باسم العلامة أو الكلمة" : "Search"}</label>
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={ar ? "بحث بالاسم، العلامة..." : "Search title or brand..."}
                  className="mt-1.5 w-full rounded-xl border border-slate-200 bg-slate-50/50 px-3 py-2 text-xs font-medium text-slate-800 outline-none focus:border-brand-500 focus:bg-white"
                />
              </div>
            </div>

            {/* Strict Filter Semantics Banner (Rule C) */}
            {hasBudget && (
              <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50/60 p-4 text-xs leading-relaxed text-amber-900">
                <div className="font-bold">
                  {ar ? "توضيح معايير التصفية المالية الصارمة:" : "Strict Financial Filter Notice:"}
                </div>
                <p className="mt-1">
                  {ar
                    ? `الفرص التي يقل حدها الأدنى الموثق عن ${parsedBudget.toLocaleString()} ر.س تظهر كفرص متطابقة ماليّاً (${budgetFitItems.length} فرصة). الفرص التي لا تعلن ميزانيتها في المصدر الرسمي (${budgetUnknownItems.length} فرصة) لا تُعتبر متطابقة آلياً منعاً للتضليل، وتتطلب إدخال ميزانية مقترحة بافتراض منك.`
                    : `Opportunities with verified minimum capex within ${parsedBudget.toLocaleString()} SAR are shown (${budgetFitItems.length} items). Opportunities with unannounced capex (${budgetUnknownItems.length} items) are classified as unknown, not auto-fit.`}
                </p>
              </div>
            )}

            {/* Opportunities Cards Grid */}
            {loading ? (
              <div className="py-24 text-center text-sm text-slate-500">
                {ar ? "جارٍ تحميل الفرص المعتمدة من السجل..." : "Loading verified opportunities..."}
              </div>
            ) : error ? (
              <div role="alert" className="mt-8 rounded-2xl bg-red-50 p-6 text-center text-sm text-red-700">
                {error}
              </div>
            ) : hasBudget ? (
              <div className="mt-8 space-y-8">
                {/* Group 1: Budget Fit Items */}
                <div>
                  <h3 className="text-sm font-bold text-slate-900">
                    {ar ? `فرص متطابقة مع ميزانيتك (أقل من ${parsedBudget.toLocaleString()} ر.س):` : `Opportunities within budget:`}
                  </h3>
                  {budgetFitItems.length === 0 ? (
                    <div data-testid="budget-fit-empty" className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-xs text-slate-600">
                      {ar ? "لا توجد فرص منشورة بحد أدنى استثماري معلن يقع ضمن هذه الميزانية." : "No opportunities with announced capex fit this budget."}
                    </div>
                  ) : (
                    <div className="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                      {budgetFitItems.map((opp) => renderCard(opp))}
                    </div>
                  )}
                </div>

                {/* Group 2: Budget Unknown Items (Isolated) */}
                <div data-testid="budget-unknown-group" className="border-t border-slate-200 pt-6">
                  <div data-testid="budget-unknown-notice" className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4 text-xs text-amber-900">
                    <span className="font-bold">{ar ? "فرص استثمارية غير محددة الميزانية بالمصدر الرسمي:" : "Opportunities with unannounced capex:"}</span>
                    <p className="mt-1">
                      {ar ? "هذه الفرص لم تعلن حداً أدنى للاستثمار في مصادرها الرسمية الموثقة، ولذلك لا تُعتبر متطابقة آلياً منعاً للتضليل المالي." : "These opportunities do not disclose capital requirements in official sources and are separated to prevent misleading auto-fit."}
                    </p>
                  </div>
                  <div className="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                    {budgetUnknownItems.map((opp) => renderCard(opp))}
                  </div>
                </div>
              </div>
            ) : items.length === 0 ? (
              <div className="py-24 text-center text-sm text-slate-500">
                {ar ? "لا توجد فرص استثمارية معتمدة تطابق معايير التصفية الحالية." : "No opportunities match current criteria."}
              </div>
            ) : (
              <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {items.map((opp) => renderCard(opp))}
              </div>
            )}
          </>
        )}

        {/* EXPLAIN FIT MODAL (WAVE 3B) */}
        {selectedMatchForExplain && (
          <div
            role="dialog"
            aria-modal="true"
            data-testid="explain-fit-modal"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
          >
            <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl sm:p-8">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-brand-50 px-2.5 py-0.5 text-xs font-bold text-brand-700">
                      {ar ? "شرح الملاءمة الحتمية" : "Deterministic Fit Breakdown"}
                    </span>
                    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-bold ${getMatchStateBadge(selectedMatchForExplain.match_state).bg}`}>
                      {ar ? getMatchStateBadge(selectedMatchForExplain.match_state).text_ar : getMatchStateBadge(selectedMatchForExplain.match_state).text_en}
                    </span>
                  </div>
                  <h3 className="mt-2 text-xl font-bold text-slate-900">
                    {ar ? selectedMatchForExplain.title_ar : selectedMatchForExplain.title_en}
                  </h3>
                  {selectedMatchForExplain.brand_name && (
                    <p className="text-xs font-semibold text-brand-700">{selectedMatchForExplain.brand_name}</p>
                  )}
                </div>
                <button
                  onClick={() => setSelectedMatchForExplain(null)}
                  className="rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              {/* Overall Decision Context */}
              <div className="mt-4 rounded-2xl bg-slate-50 p-4 text-xs leading-relaxed text-slate-700">
                <span className="font-bold text-slate-900">{ar ? "خلاصة القرار: " : "Decision Summary: "}</span>
                <span>{selectedMatchForExplain.summary_reason}</span>
              </div>

              {/* Evaluated Criteria Table */}
              <div className="mt-6 overflow-x-auto">
                <table className="w-full border-collapse text-right text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-100/70 text-slate-700">
                      <th className="p-3 font-semibold">{ar ? "المعيار" : "Criterion"}</th>
                      <th className="p-3 font-semibold">{ar ? "نوع القيد" : "Strength"}</th>
                      <th className="p-3 font-semibold">{ar ? "مدخل المستثمر" : "Investor Input"}</th>
                      <th className="p-3 font-semibold">{ar ? "الحقيقة المنشورة" : "Sourced Fact"}</th>
                      <th className="p-3 font-semibold">{ar ? "النتيجة" : "Result"}</th>
                      <th className="p-3 font-semibold">{ar ? "التعليل التفصيلي" : "Reason"}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {Object.entries(selectedMatchForExplain.criteria_evaluations).map(([key, c]) => {
                      let resBadge = "bg-slate-100 text-slate-700";
                      if (c.result === "PASS") resBadge = "bg-emerald-100 text-emerald-800";
                      else if (c.result === "FAIL") resBadge = "bg-rose-100 text-rose-800";
                      else if (c.result === "UNKNOWN") resBadge = "bg-amber-100 text-amber-800";

                      return (
                        <tr key={key} className="hover:bg-slate-50/50">
                          <td className="p-3 font-semibold text-slate-900">{c.label_ar || c.criterion}</td>
                          <td className="p-3">
                            <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                              c.constraint_strength === "HARD" ? "bg-rose-50 text-rose-700" : "bg-slate-100 text-slate-600"
                            }`}>
                              {c.constraint_strength === "HARD" ? (ar ? "حتمي (HARD)" : "HARD") : (ar ? "تفضيل (PREF)" : "PREF")}
                            </span>
                          </td>
                          <td className="p-3 font-mono text-slate-700">
                            {Array.isArray(c.user_value) ? c.user_value.join(", ") : String(c.user_value ?? "—")}
                          </td>
                          <td className="p-3 font-mono text-slate-700">
                            {Array.isArray(c.opportunity_value) ? c.opportunity_value.join(", ") : String(c.opportunity_value ?? "—")}
                          </td>
                          <td className="p-3">
                            <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${resBadge}`}>
                              {c.result}
                            </span>
                          </td>
                          <td className="max-w-xs p-3 leading-relaxed text-slate-600">
                            {c.reason}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Source Verification Footer */}
              <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4 text-xs text-slate-500">
                <div>
                  <span className="font-semibold text-slate-700">{ar ? "المصدر المعتمد: " : "Source: "}</span>
                  <a
                    href={selectedMatchForExplain.official_source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-brand-700 hover:underline"
                  >
                    {selectedMatchForExplain.official_source_url} ↗
                  </a>
                </div>
                <button
                  onClick={() => setSelectedMatchForExplain(null)}
                  className="rounded-xl bg-slate-100 px-5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200"
                >
                  {ar ? "إغلاق" : "Close"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* OPPORTUNITY DETAIL MODAL */}
        {detailItem && (
          <div
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
          >
            <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl sm:p-8">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-purple-100 px-2 py-0.5 text-xs font-bold text-purple-800">
                      {detailItem.opportunity_type === "FRANCHISE" ? (ar ? "امتياز تجاري" : "Franchise") : (ar ? "فرصة استثمارية" : "Business Opportunity")}
                    </span>
                    <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-800">
                      {detailItem.verification_status}
                    </span>
                  </div>
                  <h3 className="mt-2 text-xl font-bold text-slate-900">
                    {ar ? detailItem.title_ar : detailItem.title_en}
                  </h3>
                  {detailItem.brand_name && (
                    <p className="text-xs font-semibold text-brand-700">{detailItem.brand_name}</p>
                  )}
                </div>
                <button
                  onClick={() => setDetailItem(null)}
                  className="rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              {/* Facts and Provenance Details */}
              <div className="mt-6 space-y-6 text-xs">
                <div>
                  <h4 className="font-bold text-slate-900">{ar ? "الوصف الرسمي الكامل:" : "Full Official Description:"}</h4>
                  <p className="mt-2 leading-relaxed text-slate-700">
                    {ar ? detailItem.description_ar : detailItem.description_en}
                  </p>
                </div>

                {/* 1. Published & Verified Facts */}
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50/40 p-4">
                  <h4 className="font-bold text-emerald-900">
                    {ar ? "معلومات منشورة وموثقة:" : "Published and Verified Facts:"}
                  </h4>
                  <div className="mt-2 space-y-1.5 text-emerald-950">
                    <p>• {ar ? "العلامة والنشاط موثقان رسمياً بسجل الفرص." : "Brand and activity are officially verified in registry."}</p>
                    {detailItem.investment_min && (
                      <p>• {ar ? `النطاق الاستثماري الموثق: ${fmtSAR(detailItem.investment_min, locale)} – ${fmtSAR(detailItem.investment_max, locale)}` : `Verified Capex: ${fmtSAR(detailItem.investment_min, locale)} – ${fmtSAR(detailItem.investment_max, locale)}`}</p>
                    )}
                    {detailItem.franchise_fee !== null && detailItem.franchise_fee !== undefined && (
                      <p>• {ar ? `رسوم الامتياز الموثقة: ${fmtSAR(detailItem.franchise_fee, locale)}` : `Verified Franchise Fee: ${fmtSAR(detailItem.franchise_fee, locale)}`}</p>
                    )}
                  </div>
                </div>

                {/* 2. Platform Taxonomy */}
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                  <h4 className="font-bold text-slate-900">
                    {ar ? "تصنيف المنصة المعياري:" : "Platform Taxonomy:"}
                  </h4>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-slate-700">
                    <div><span className="text-slate-500">{ar ? "القطاع:" : "Sector:"}</span> {detailItem.sector}</div>
                    <div><span className="text-slate-500">{ar ? "النوع:" : "Type:"}</span> {detailItem.opportunity_type}</div>
                    <div><span className="text-slate-500">{ar ? "النطاق:" : "Geography:"}</span> {detailItem.city ? `${detailItem.city} (${detailItem.region || ""})` : (ar ? "وطني شامل" : "National")}</div>
                  </div>
                </div>

                {/* 3. Unannounced Facts */}
                <div className="rounded-2xl border border-amber-200 bg-amber-50/40 p-4">
                  <h4 className="font-bold text-amber-900">
                    {ar ? "معلومات غير معلنة:" : "Unannounced Facts:"}
                  </h4>
                  <div className="mt-2 space-y-1 text-amber-950">
                    {!detailItem.investment_min && (
                      <p>• {ar ? "الحد الأدنى للاستثمار الرأسمالي (Capex) غير معلن في البوابة العامة للعلامة." : "Minimum capital investment (Capex) is not disclosed in the public portal."}</p>
                    )}
                    {(detailItem.franchise_fee === null || detailItem.franchise_fee === undefined) && detailItem.opportunity_type === "FRANCHISE" && (
                      <p>• {ar ? "رسوم الفرانشايز التفصيلية غير معلنة وتتطلب تواصلاً مباشراً." : "Franchise fee details are unannounced and require direct brand outreach."}</p>
                    )}
                  </div>
                </div>

                {/* 4. Required Investor Assumptions */}
                <div className="rounded-2xl border border-blue-200 bg-blue-50/40 p-4">
                  <h4 className="font-bold text-blue-900">
                    {ar ? "افتراضات مطلوبة من المستثمر:" : "Required Investor Assumptions:"}
                  </h4>
                  <div className="mt-2 space-y-1 text-blue-950">
                    <p>• {ar ? "تحديد ميزانية رأسمالية تقديرية لدراسة الجدوى المالية (افتراض مستثمر)." : "Specify estimated capital budget for financial feasibility (investor assumption)."}</p>
                    <p>• {ar ? "اختيار المدينة وموقع الفرع وتكاليف الإيجار والتشغيل المحلي." : "Select target city, site, local rent, and operating assumptions."}</p>
                  </div>
                </div>

                {/* Primary Source Provenance */}
                <div className="rounded-2xl border border-slate-200 p-4">
                  <h4 className="font-bold text-slate-900">{ar ? "وثائق المصدر الأولي وسلسلة الأصل:" : "Primary Source Lineage:"}</h4>
                  <div className="mt-3 space-y-2">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
                      <span className="text-slate-600">{ar ? "توثيق وجود الفرصة بالمصدر الأولي:" : "Opportunity Existence Proof:"}</span>
                      <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-[11px] font-medium text-emerald-800">
                        {ar ? "موثق بمصدر أولي مستقل ↗" : "Verified Primary Source ↗"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
                      <span className="text-slate-600">{ar ? "الاستثمار الرأسمالي (Capex Min/Max):" : "Investment Range:"}</span>
                      <span className="rounded-md bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800">
                        {detailItem.investment_min
                          ? (ar ? "موثق من المصدر" : "Source-verified")
                          : (ar ? "غير معلن - يتطلب افتراض مستثمر" : "Unannounced (Requires Investor Assumption)")}
                      </span>
                    </div>
                    <div className="flex items-center justify-between border-b border-slate-100 pb-1.5">
                      <span className="text-slate-600">{ar ? "المصدر المعتمد:" : "Official Source:"}</span>
                      <a
                        href={detailItem.official_source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-brand-700 hover:underline"
                      >
                        {detailItem.source_owner} ({detailItem.official_source_url}) ↗
                      </a>
                    </div>
                  </div>
                </div>
              </div>

              {/* Modal Actions */}
              <div className="mt-6 flex items-center justify-end gap-3 border-t border-slate-100 pt-4">
                <button
                  onClick={() => setDetailItem(null)}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  {ar ? "إغلاق" : "Close"}
                </button>
                <button
                  onClick={() => {
                    const target = detailItem;
                    setDetailItem(null);
                    openCreateStudy(target);
                  }}
                  className="rounded-xl bg-brand-600 px-5 py-2 text-xs font-semibold text-white shadow hover:bg-brand-700"
                >
                  {ar ? "إنشاء دراسة جدوى من هذه الفرصة" : "Create Study from this Opportunity"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* CREATE STUDY MODAL */}
        {targetForStudy && (
          <div
            role="dialog"
            aria-modal="true"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-sm"
          >
            <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl sm:p-8">
              <h3 className="text-xl font-bold text-slate-900">
                {ar ? "إنشاء دراسة جدوى من فرصة حقيقية" : "Create Feasibility Study from Opportunity"}
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600">
                {ar
                  ? "سيتم إنشاء مساحة مشروع ودراسة جدوى حقيقية دائمة، مع نقل البيانات الموثقة من المصدر وحفظ سلسلة الأصل والتوثيق (Lineage) دون أي أرقام مفبركة."
                  : "A persistent study will be initialized with immutable source lineage and verified facts transferred."}
              </p>

              <div className="mt-5 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "عنوان الدراسة" : "Study Title"}
                  </label>
                  <input
                    type="text"
                    value={studyTitle}
                    onChange={(e) => setStudyTitle(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-slate-300 p-3 text-xs outline-none focus:border-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700">
                    {ar ? "الميزانية المبدئية المقترحة (ر.س)" : "Proposed Investment Budget (SAR)"}
                    <span className="mx-1 text-[11px] font-normal text-slate-500">
                      {targetForStudy.investment_min
                        ? (ar ? "(مأخوذ من المصدر الرسمي كحد أدنى)" : "(from verified source minimum)")
                        : (ar ? "(افتراض مستخدم USER_ASSUMPTION - غير معلن في المصدر)" : "(user assumption)")}
                    </span>
                  </label>
                  <input
                    type="number"
                    min={10000}
                    placeholder={ar ? "أدخل ميزانيتك المقترحة (مثال: 450,000)" : "Enter proposed budget (e.g. 450,000)"}
                    value={customBudget}
                    onChange={(e) => setCustomBudget(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-slate-300 p-3 font-mono text-xs outline-none focus:border-brand-500"
                  />
                </div>

                <div className="rounded-2xl bg-slate-50 p-3 text-xs text-slate-600">
                  <p className="font-semibold text-slate-800">{ar ? "الحقائق المنقولة رسمياً:" : "Transferred Lineage:"}</p>
                  <p className="mt-1 text-[11px]">
                    {ar ? "القطاع:" : "Sector:"} {targetForStudy.sector} · {ar ? "المصدر:" : "Source:"} {targetForStudy.source_owner} · {ar ? "الإصدار:" : "Version:"} {targetForStudy.data_version}
                  </p>
                  {studyMatchResultId && (
                    <p className="mt-1 text-[11px] font-semibold text-brand-700">
                      {ar ? "✓ سيتم إرفاق لقطة المطابقة (Fit Snapshot) في حمولة الدراسة" : "✓ Fit Snapshot will be attached to study payload"}
                    </p>
                  )}
                </div>

                {createStudyError && (
                  <p role="alert" className="rounded-xl bg-red-50 p-3 text-xs text-red-700">{createStudyError}</p>
                )}
              </div>

              <div className="mt-6 flex items-center justify-end gap-3 border-t border-slate-100 pt-4">
                <button
                  onClick={() => setTargetForStudy(null)}
                  disabled={creatingStudy}
                  className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  {ar ? "إلغاء" : "Cancel"}
                </button>
                <button
                  onClick={handleConfirmCreateStudy}
                  disabled={creatingStudy}
                  className="rounded-xl bg-brand-600 px-5 py-2.5 text-xs font-semibold text-white shadow hover:bg-brand-700 disabled:opacity-50"
                >
                  {creatingStudy ? (ar ? "جارٍ إنشاء الدراسة..." : "Creating Study...") : (ar ? "تأكيد وبدء الدراسة" : "Confirm & Launch Study")}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
