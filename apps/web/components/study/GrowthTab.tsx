"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getGrowthWorkspace,
  createGrowthScenario,
  runGrowthWhatIf,
  createGrowthReview,
  recordGrowthDecision,
  createGrowthAction,
  updateGrowthAction,
  getGrowthFundingContext,
  type GrowthWorkspaceData,
  type GrowthFundingContext,
} from "@/lib/api";

const healthStatusMap: Record<string, { ar: string; badge: string; desc: string }> = {
  HEALTHY: {
    ar: "صحي ومستقر (HEALTHY)",
    badge: "bg-emerald-100 text-emerald-800 border-emerald-300",
    desc: "أداء تشغيلي إيجابي، هوامش مستقرة، ومدرج سيولة يتجاوز 6 أشهر.",
  },
  WATCH: {
    ar: "قيد المراقبة والتحفظ (WATCH)",
    badge: "bg-amber-100 text-amber-800 border-amber-300",
    desc: "هناك تراجع في بعض مؤشرات الكفاءة أو مدرج سيولة بين 3 و 6 أشهر.",
  },
  AT_RISK: {
    ar: "حرج / معرض للمخاطر (AT_RISK)",
    badge: "bg-red-100 text-red-800 border-red-300 animate-pulse",
    desc: "مدرج السيولة أقل من 3 أشهر أو خسائر تشغيلية متراكمة تتطلب تدخلاً عاجلاً.",
  },
  INSUFFICIENT_DATA: {
    ar: "بيانات غير كافية للتقييم (INSUFFICIENT_DATA)",
    badge: "bg-slate-100 text-slate-700 border-slate-300",
    desc: "لا توجد دورات تشغيلية فعلية كافية (يلزم تسجيل دورة واحدة على الأقل في نظام الإطلاق).",
  },
};

const trendDirectionMap: Record<string, { ar: string; badge: string }> = {
  IMPROVING: { ar: "في تحسن مستمر", badge: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  STABLE: { ar: "مستقر", badge: "bg-blue-50 text-blue-700 border-blue-200" },
  DETERIORATING: { ar: "في تراجع", badge: "bg-red-50 text-red-700 border-red-200" },
  INSUFFICIENT_DATA: { ar: "بيانات غير كافية (يلزم دورتين)", badge: "bg-slate-50 text-slate-600 border-slate-200" },
};

const readinessMap: Record<string, { ar: string; badge: string }> = {
  READY: { ar: "جاهز للتوسع المدروس (READY)", badge: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  CONDITIONALLY_READY: { ar: "جاهز بشروط محددة (CONDITIONALLY_READY)", badge: "bg-blue-100 text-blue-800 border-blue-300" },
  NOT_READY: { ar: "غير جاهز للتوسع حالياً (NOT_READY)", badge: "bg-red-100 text-red-800 border-red-300" },
  NEEDS_INFORMATION: { ar: "يلزم استكمال البيانات (NEEDS_INFORMATION)", badge: "bg-amber-100 text-amber-800 border-amber-300" },
};

const riskLevelMap: Record<string, { ar: string; badge: string }> = {
  LOW: { ar: "منخفض / آمن", badge: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  WATCH: { ar: "مراقبة وتحفظ", badge: "bg-amber-50 text-amber-700 border-amber-200" },
  HIGH: { ar: "عالي / خطر حرج", badge: "bg-red-50 text-red-700 border-red-200" },
  UNKNOWN: { ar: "غير محدد لغياب البيانات", badge: "bg-slate-50 text-slate-600 border-slate-200" },
};

function formatSAR(val: number | null | undefined): string {
  if (val == null || isNaN(val)) return "—";
  return new Intl.NumberFormat("ar-SA", {
    style: "currency",
    currency: "SAR",
    maximumFractionDigits: 0,
  }).format(val);
}

export default function GrowthTab({
  studyId,
  token,
  locale = "ar",
  onNavigateTab,
}: {
  studyId: number;
  token: string;
  locale?: "ar" | "en";
  onNavigateTab?: (tab: string, targetId?: number) => void;
}) {
  const ar = locale === "ar";
  const [data, setData] = useState<GrowthWorkspaceData | null>(null);
  const [subTab, setSubTab] = useState<
    "health" | "trends" | "unit_econ" | "risks" | "scenarios" | "what_if" | "funding" | "reviews" | "decisions"
  >("health");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Scenario-specific Funding Context state
  const [fundingScenarioId, setFundingScenarioId] = useState<number | null>(null);
  const [scenarioFunding, setScenarioFunding] = useState<GrowthFundingContext | null>(null);
  const [loadingFunding, setLoadingFunding] = useState(false);
  const [fundingError, setFundingError] = useState<string | null>(null);

  // Scenario form state
  const [scenarioName, setScenarioName] = useState("");
  const [scenarioType, setScenarioType] = useState("NEW_BRANCH");
  const [scenarioDesc, setScenarioDesc] = useState("");
  const [scenarioHorizon, setScenarioHorizon] = useState(12);
  const [scenarioCapex, setScenarioCapex] = useState<number | "">("");
  const [scenarioOpex, setScenarioOpex] = useState<number | "">("");
  const [scenarioRevenueUplift, setScenarioRevenueUplift] = useState<number | "">("");
  const [scenarioCapacityUplift, setScenarioCapacityUplift] = useState<number | "">("");
  const [submittingScenario, setSubmittingScenario] = useState(false);

  // What-If runner state
  const [whatIfName, setWhatIfName] = useState("محاكاة توسع افتراضية");
  const [whatIfType, setWhatIfType] = useState("CAPACITY_EXPANSION");
  const [whatIfHorizon, setWhatIfHorizon] = useState(12);
  const [whatIfCapex, setWhatIfCapex] = useState<number | "">("");
  const [whatIfOpex, setWhatIfOpex] = useState<number | "">("");
  const [whatIfRevenue, setWhatIfRevenue] = useState<number | "">("");
  const [runningWhatIf, setRunningWhatIf] = useState(false);

  // Monthly Review form state
  const [reviewPeriod, setReviewPeriod] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewTargetNext, setReviewTargetNext] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);

  // Decision form state
  const [decisionType, setDecisionType] = useState<"SCALE" | "FIX" | "PIVOT" | "HOLD" | "STOP" | "NEEDS_INFORMATION">("HOLD");
  const [decisionReason, setDecisionReason] = useState("");
  const [decisionScenarioId, setDecisionScenarioId] = useState<number | "">("");
  const [decisionConditions, setDecisionConditions] = useState("");
  const [decisionReEvalDate, setDecisionReEvalDate] = useState("");
  const [submittingDecision, setSubmittingDecision] = useState(false);

  // Manual action state
  const [newActionTitle, setNewActionTitle] = useState("");
  const [newActionType, setNewActionType] = useState("REMEDIATION");
  const [newActionCategory, setNewActionCategory] = useState("OPERATIONS");
  const [submittingAction, setSubmittingAction] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getGrowthWorkspace(token, studyId);
      setData(res);
    } catch (err: any) {
      setError(err?.message || "فشل تحميل بيانات بيئة إدارة النمو (Growth OS)");
    } finally {
      setLoading(false);
    }
  }, [studyId, token]);

  const loadScenarioFunding = useCallback(async (scenarioId: number | null) => {
    // Immediately clear previous scenario data and errors to prevent stale numbers
    setScenarioFunding(null);
    setFundingError(null);
    if (!scenarioId) {
      setLoadingFunding(false);
      return;
    }
    try {
      setLoadingFunding(true);
      const res = await getGrowthFundingContext(token, studyId, scenarioId);
      setScenarioFunding(res.funding_context);
    } catch (err: any) {
      // Strictly set error; never leave stale scenario data or invent numbers
      setScenarioFunding(null);
      setFundingError(err?.message || "تعذر تحميل سياق التمويل للسيناريو المحدد");
    } finally {
      setLoadingFunding(false);
    }
  }, [studyId, token]);

  const handleScenarioFundingChange = (scenarioId: number | null) => {
    // Immediately clear previous scenario data and errors on switch
    setScenarioFunding(null);
    setFundingError(null);
    setFundingScenarioId(scenarioId);
    loadScenarioFunding(scenarioId);
  };

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateScenario = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data) return;
    try {
      setSubmittingScenario(true);
      await createGrowthScenario(token, data.workspace.id, {
        name: scenarioName,
        scenario_type: scenarioType,
        description: scenarioDesc || undefined,
        target_horizon_months: Number(scenarioHorizon),
        capex_required: scenarioCapex === "" ? null : Number(scenarioCapex),
        additional_monthly_opex: scenarioOpex === "" ? null : Number(scenarioOpex),
        expected_monthly_revenue_uplift: scenarioRevenueUplift === "" ? null : Number(scenarioRevenueUplift),
        target_capacity_increase_pct: scenarioCapacityUplift === "" ? null : Number(scenarioCapacityUplift),
      });
      setActionSuccess("تم إنشاء سيناريو النمو بنجاح");
      setScenarioName("");
      setScenarioDesc("");
      setScenarioCapex("");
      setScenarioOpex("");
      setScenarioRevenueUplift("");
      setScenarioCapacityUplift("");
      loadData();
    } catch (err: any) {
      setError(err?.message || "فشل إنشاء السيناريو");
    } finally {
      setSubmittingScenario(false);
    }
  };

  const handleRunWhatIf = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data) return;
    try {
      setRunningWhatIf(true);
      await runGrowthWhatIf(token, data.workspace.id, {
        scenario_name: whatIfName,
        scenario_type: whatIfType,
        target_horizon_months: Number(whatIfHorizon),
        capex_required: whatIfCapex === "" ? null : Number(whatIfCapex),
        additional_monthly_opex: whatIfOpex === "" ? null : Number(whatIfOpex),
        expected_monthly_revenue_uplift: whatIfRevenue === "" ? null : Number(whatIfRevenue),
      });
      setActionSuccess("تم تنفيذ محاكاة التوسع وتوليد التوقعات بنجاح");
      loadData();
    } catch (err: any) {
      setError(err?.message || "فشل تشغيل محاكاة التوسع");
    } finally {
      setRunningWhatIf(false);
    }
  };

  const handleCreateReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data) return;
    try {
      setSubmittingReview(true);
      await createGrowthReview(token, data.workspace.id, {
        review_period: reviewPeriod,
        review_notes: reviewNotes || undefined,
        target_next_month: reviewTargetNext || undefined,
      });
      setActionSuccess(`تم تجميد المراجعة الشهرية للدورة ${reviewPeriod} بنجاح`);
      setReviewPeriod("");
      setReviewNotes("");
      setReviewTargetNext("");
      loadData();
    } catch (err: any) {
      setError(err?.message || "فشل حفظ المراجعة الشهرية");
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleRecordDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data) return;
    try {
      setSubmittingDecision(true);
      const condList = decisionConditions
        ? decisionConditions.split("\n").map((s) => s.trim()).filter(Boolean)
        : [];
      await recordGrowthDecision(token, data.workspace.id, {
        decision: decisionType,
        decision_reason: decisionReason,
        growth_scenario_id: decisionType === "SCALE" && decisionScenarioId ? Number(decisionScenarioId) : null,
        conditions: condList,
        re_evaluation_date: decisionReEvalDate || null,
      });
      setActionSuccess(`تم اعتماد وتسجيل القرار الاستراتيجي '${decisionType}' بنجاح`);
      setDecisionReason("");
      setDecisionScenarioId("");
      setDecisionConditions("");
      setDecisionReEvalDate("");
      loadData();
    } catch (err: any) {
      setError(err?.message || "فشل تسجيل القرار");
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleCreateAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!data || !newActionTitle.trim()) return;
    try {
      setSubmittingAction(true);
      await createGrowthAction(token, data.workspace.id, {
        title: newActionTitle.trim(),
        action_type: newActionType,
        category: newActionCategory,
      });
      setActionSuccess("تم إضافة بند العمل بنجاح");
      setNewActionTitle("");
      loadData();
    } catch (err: any) {
      setError(err?.message || "فشل إضافة بند العمل");
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleToggleActionStatus = async (actionId: number, currentStatus: string) => {
    try {
      const nextStatus = currentStatus === "COMPLETED" ? "PENDING" : "COMPLETED";
      await updateGrowthAction(token, actionId, { status: nextStatus });
      loadData();
    } catch (err: any) {
      setError(err?.message || "فشل تحديث حالة الإجراء");
    }
  };

  if (loading && !data) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-brand-600 border-t-transparent" />
        <span className="mr-3 text-sm font-medium text-slate-600">جارٍ تحميل نظام إدارة وتوسع الأعمال (Growth OS)...</span>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-center text-red-700">
        <p className="font-bold">تعذر تحميل بيئة إدارة النمو</p>
        <p className="mt-1 text-xs">{error || "تأكد من الاتصال بالخادم وصلاحيات الوصول."}</p>
        <button
          onClick={loadData}
          className="mt-4 rounded-xl bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-700"
        >
          إعادة المحاولة
        </button>
      </div>
    );
  }

  const { business_health, trends, unit_economics, risks, expansion_readiness, growth_funding } = data;

  return (
    <div className="space-y-6" dir={ar ? "rtl" : "ltr"} data-testid="growth-os-workspace">
      {/* Header Banner */}
      <div className="rounded-3xl border border-slate-200 bg-gradient-to-r from-emerald-900 via-slate-900 to-ink-900 p-6 text-white shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-emerald-500/20 px-2.5 py-1 text-xs font-bold text-emerald-300 border border-emerald-500/30">
                WAVE 6 — GROWTH OS
              </span>
              <span className="text-xs text-slate-400">
                حالة بيئة العمل: {data.workspace.status} | عدد الدورات الفعلية: {data.actual_periods_count}
              </span>
            </div>
            <h2 className="mt-2 text-2xl font-black text-white">نظام إدارة وتوسع الأعمال (Growth OS)</h2>
            <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-300">
              حوكمة تشغيلية مبنية على الأدلة والبيانات الفعلية: صحة النشاط، الاتجاهات، اقتصاديات الوحدة، المخاطر، المحاكاة المالية للتوسع، والقرارات الاستراتيجية (SCALE / FIX / PIVOT / HOLD / STOP).
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <span
              data-testid="growth-health-state"
              className={`rounded-xl border px-3 py-1.5 text-xs font-bold ${
                healthStatusMap[business_health.health_state]?.badge || "bg-slate-100 text-slate-800"
              }`}
            >
              {healthStatusMap[business_health.health_state]?.ar || business_health.health_state}
            </span>
            <span className="text-[11px] text-slate-400">إصدار المحرك: {business_health.calculation_version}</span>
          </div>
        </div>
      </div>

      {/* Notifications */}
      {actionSuccess && (
        <div className="flex items-center justify-between rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-xs font-medium text-emerald-800">
          <span>{actionSuccess}</span>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-600 hover:text-emerald-900">✕</button>
        </div>
      )}
      {error && (
        <div className="flex items-center justify-between rounded-2xl border border-red-200 bg-red-50 p-4 text-xs font-medium text-red-800">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-600 hover:text-red-900">✕</button>
        </div>
      )}

      {/* 9 Persistent Sub-tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {[
          { id: "health", label: "صحة الأعمال", badge: business_health.health_state },
          { id: "trends", label: "الاتجاهات التشغيلية", count: trends.periods_analyzed },
          { id: "unit_econ", label: "اقتصاديات الوحدة", badge: unit_economics.period_label },
          { id: "risks", label: "المخاطر", count: risks.length },
          { id: "scenarios", label: "فرص وسيناريوهات النمو", count: data.scenarios.length },
          { id: "what_if", label: "محاكاة التوسع (What-If)", count: data.what_if_models.length },
          { id: "funding", label: "التمويل للنمو", count: growth_funding.wave2_matched_programs_count },
          { id: "reviews", label: "المراجعة الشهرية", count: data.monthly_reviews.length },
          { id: "decisions", label: "القرار الاستراتيجي", count: data.decisions.length },
        ].map((tab) => (
          <button
            key={tab.id}
            data-testid={`growth-subtab-${tab.id}`}
            onClick={() => setSubTab(tab.id as any)}
            className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-bold transition-all ${
              subTab === tab.id
                ? "bg-emerald-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={`rounded-full px-1.5 py-0.5 text-[10px] font-extrabold ${
                  subTab === tab.id ? "bg-emerald-800 text-white" : "bg-slate-200 text-slate-800"
                }`}
              >
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* SUB-TAB 1: BUSINESS HEALTH */}
      {subTab === "health" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">تقييم صحة الأعمال (Business Health Engine)</h3>
                <p className="mt-1 text-xs text-slate-500">
                  تشخيص دقيق مبني على الانحرافات الفعلية ومدرج السيولة التشغيلي الحقيقي دون تفاؤل مصطنع.
                </p>
              </div>
              <span
                className={`rounded-xl border px-3 py-1.5 text-xs font-bold ${
                  healthStatusMap[business_health.health_state]?.badge
                }`}
              >
                {healthStatusMap[business_health.health_state]?.ar}
              </span>
            </div>

            <div className="mt-4 rounded-xl bg-slate-50 p-4 border border-slate-200">
              <h4 className="text-xs font-bold text-slate-700">ملخص التشخيص:</h4>
              <p className="mt-1 text-xs leading-relaxed text-slate-600">{business_health.health_summary_ar}</p>
              <div className="mt-3 border-t border-slate-200 pt-3">
                <span className="text-xs font-bold text-emerald-800">التوصية التشغيلية: </span>
                <span className="text-xs text-slate-700">{business_health.recommendation_ar}</span>
              </div>
            </div>

            <div className="mt-6">
              <h4 className="text-xs font-bold text-slate-700">المؤشرات الداعمة للتقييم:</h4>
              <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {Object.entries(business_health.supporting_metrics || {}).map(([k, v]: [string, any]) => (
                  <div key={k} className="rounded-xl border border-slate-200 bg-white p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-slate-500">{k}</span>
                      <span
                        className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                          v?.classification === "ACTUAL"
                            ? "bg-emerald-100 text-emerald-800"
                            : v?.classification === "PLATFORM_DERIVED"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {v?.classification === "ACTUAL"
                          ? "بيانات فعلية"
                          : v?.classification === "PLATFORM_DERIVED"
                          ? "مشتق من المنصة"
                          : "غير متوفر"}
                      </span>
                    </div>
                    <div className="mt-2 text-base font-black text-slate-900">
                      {v?.value !== null && v?.value !== undefined ? String(v?.value) : "غير متوفر"}
                    </div>
                    {v?.note_ar && <p className="mt-1 text-[10px] text-slate-500">{v.note_ar}</p>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 2: TRENDS */}
      {subTab === "trends" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">تحليل الاتجاهات التشغيلية (Trends Analysis)</h3>
                <p className="mt-1 text-xs text-slate-500">
                  مقارنة أداء الدورات المتعاقبة لتحديد ما إذا كان النشاط يتحسن، يستقر، أو يتراجع (يلزم دورتين على الأقل).
                </p>
              </div>
              <span className="rounded-xl bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700">
                الدورات المحللة: {trends.periods_analyzed}
              </span>
            </div>

            <div className="mt-4 rounded-xl bg-slate-50 p-4 border border-slate-200">
              <p className="text-xs text-slate-700 leading-relaxed">{trends.evaluation_summary_ar}</p>
            </div>

            <div className="mt-6 space-y-4">
              {Object.entries(trends.metrics || {}).map(([metricKey, m]) => (
                <div key={metricKey} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                    <div>
                      <span className="text-xs font-bold text-slate-800">{m.metric_name_ar}</span>
                      <span className="mr-2 text-[11px] text-slate-400">({m.period_range})</span>
                    </div>
                    <span
                      className={`rounded-lg border px-2.5 py-1 text-xs font-bold ${
                        trendDirectionMap[m.direction]?.badge || "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {trendDirectionMap[m.direction]?.ar || m.direction}
                    </span>
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
                    <div>
                      <span className="text-slate-400 block text-[11px]">القيمة الأولى:</span>
                      <span className="font-bold text-slate-700">
                        {m.first_value !== null ? m.first_value.toLocaleString() : "غير متوفر"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">آخر قيمة فعلية:</span>
                      <span className="font-bold text-slate-900">
                        {m.latest_value !== null ? m.latest_value.toLocaleString() : "غير متوفر"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">التغير المطلق:</span>
                      <span
                        className={`font-bold ${
                          (m.absolute_change || 0) >= 0 ? "text-emerald-700" : "text-red-700"
                        }`}
                      >
                        {m.absolute_change !== null
                          ? `${(m.absolute_change || 0) > 0 ? "+" : ""}${m.absolute_change.toLocaleString()}`
                          : "غير متوفر"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[11px]">نسبة التغير:</span>
                      <span
                        className={`font-bold ${
                          (m.percentage_change || 0) >= 0 ? "text-emerald-700" : "text-red-700"
                        }`}
                      >
                        {m.percentage_change !== null
                          ? `${(m.percentage_change || 0) > 0 ? "+" : ""}${m.percentage_change}%`
                          : "غير متوفر (مقام صفري أو بيانات مفقودة)"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: UNIT ECONOMICS */}
      {subTab === "unit_econ" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900">اقتصاديات الوحدة (Unit Economics)</h3>
                <p className="mt-1 text-xs text-slate-500">
                  حساب دقيق لمتوسط قيمة الطلب، تكلفة اكتساب العميل (CAC)، وهامش المساهمة مع إيضاح المعادلات.
                </p>
              </div>
              <span className="rounded-xl bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700">
                الدورة المعتمدة: {unit_economics.period_label}
              </span>
            </div>

            <div className="mt-4 rounded-xl bg-slate-50 p-4 border border-slate-200">
              <p className="text-xs text-slate-700 leading-relaxed">{unit_economics.calculation_summary_ar}</p>
            </div>

            <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Object.entries(unit_economics.metrics || {}).map(([key, item]) => (
                <div key={key} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="text-xs font-bold text-slate-800">{item.name_ar}</span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                        item.is_known
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {item.is_known ? "محسوب فعلياً" : "غير متوفر"}
                    </span>
                  </div>
                  <div className="mt-3">
                    <span className="text-xl font-black text-slate-900">
                      {item.value !== null ? item.value.toLocaleString() : "—"}
                    </span>
                    <span className="mr-1 text-xs text-slate-500">{item.unit}</span>
                  </div>
                  <div className="mt-2 text-[10px] text-slate-500">
                    <span className="font-bold">المعادلة: </span>
                    <span>{item.formula_ar}</span>
                  </div>
                  {item.note_ar && <p className="mt-1 text-[10px] text-amber-700">{item.note_ar}</p>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 4: RISKS */}
      {subTab === "risks" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="border-b border-slate-100 pb-4">
              <h3 className="text-lg font-bold text-slate-900">سجل المخاطر التشغيلية والمالية (Operational & Financial Risks)</h3>
              <p className="mt-1 text-xs text-slate-500">
                كشف شفاف واستباقي للمخاطر التشغيلية، عجز السيولة، وضغط الهوامش مع تدابير المعالجة.
              </p>
            </div>

            <div className="mt-6 space-y-4">
              {risks.length === 0 ? (
                <p className="text-center text-xs text-slate-500 py-8">لا توجد مخاطر مرصودة حالياً.</p>
              ) : (
                risks.map((r, idx) => (
                  <div key={idx} className="rounded-xl border border-slate-200 bg-white p-4">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                      <span className="text-xs font-bold text-slate-900">{r.risk_title_ar}</span>
                      <span
                        className={`rounded-lg border px-2.5 py-1 text-xs font-bold ${
                          riskLevelMap[r.level]?.badge || "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {riskLevelMap[r.level]?.ar || r.level}
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 text-xs">
                      <div className="rounded-lg bg-slate-50 p-3">
                        <span className="font-bold text-slate-700 block mb-1">الأدلة والقرائن:</span>
                        <span className="text-slate-600 leading-relaxed">{r.evidence_ar}</span>
                      </div>
                      <div className="rounded-lg bg-emerald-50 p-3">
                        <span className="font-bold text-emerald-800 block mb-1">إجراء المعالجة المقترح:</span>
                        <span className="text-emerald-900 leading-relaxed">{r.remedy_ar}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 5: SCENARIOS */}
      {subTab === "scenarios" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="border-b border-slate-100 pb-4">
              <h3 className="text-lg font-bold text-slate-900">سيناريوهات النمو والتوسع (Growth Scenarios)</h3>
              <p className="mt-1 text-xs text-slate-500">
                صياغة سيناريوهات نمو منضبطة (فرع جديد، رفع طاقة استيعابية، تحسين أسعار، خفض تكاليف).
              </p>
            </div>

            {/* Create Scenario Form */}
            <form onSubmit={handleCreateScenario} className="mt-6 rounded-xl bg-slate-50 p-4 border border-slate-200 space-y-4">
              <h4 className="text-xs font-bold text-slate-800">إضافة سيناريو نمو جديد</h4>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">اسم السيناريو</label>
                  <input
                    type="text"
                    required
                    value={scenarioName}
                    onChange={(e) => setScenarioName(e.target.value)}
                    placeholder="مثال: افتتاح فرع الرياض الثاني"
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">نوع السيناريو</label>
                  <select
                    value={scenarioType}
                    onChange={(e) => setScenarioType(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  >
                    <option value="NEW_BRANCH">افتتاح فرع إضافي (NEW_BRANCH)</option>
                    <option value="CAPACITY_EXPANSION">توسيع الطاقة الإنتاجية (CAPACITY_EXPANSION)</option>
                    <option value="PRODUCT_EXPANSION">إضافة خط إنتاج أو منتج جديد (PRODUCT_EXPANSION)</option>
                    <option value="PRICE_OPTIMIZATION">تحسين وتعديل الأسعار (PRICE_OPTIMIZATION)</option>
                    <option value="COST_REDUCTION">برنامج كفاءة وخفض المصاريف (COST_REDUCTION)</option>
                    <option value="DIGITAL_TRANSFORMATION">التحول الرقمي والمبيعات الإلكترونية (DIGITAL_TRANSFORMATION)</option>
                    <option value="FRANCHISE_EXPANSION">التوسع عبر منح الامتياز التجاري (FRANCHISE_EXPANSION)</option>
                    <option value="OTHER">أخرى (OTHER)</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">أفق التوقع (بالأشهر)</label>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={scenarioHorizon}
                    onChange={(e) => setScenarioHorizon(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">رأس المال الاستثماري المطلوب (CAPEX)</label>
                  <input
                    type="number"
                    min="0"
                    value={scenarioCapex}
                    onChange={(e) => setScenarioCapex(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="ر.س"
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">المصاريف التشغيلية الشهرية الإضافية (OPEX)</label>
                  <input
                    type="number"
                    min="0"
                    value={scenarioOpex}
                    onChange={(e) => setScenarioOpex(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="ر.س / شهر"
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">نمو الإيراد الشهري المتوقع</label>
                  <input
                    type="number"
                    min="0"
                    value={scenarioRevenueUplift}
                    onChange={(e) => setScenarioRevenueUplift(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="ر.س / شهر"
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={submittingScenario}
                className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {submittingScenario ? "جارٍ الحفظ..." : "حفظ السيناريو"}
              </button>
            </form>

            {/* List Scenarios */}
            <div className="mt-6 space-y-3">
              <h4 className="text-xs font-bold text-slate-800">السيناريوهات المحفوظة ({data.scenarios.length})</h4>
              {data.scenarios.map((sc) => (
                <div key={sc.id} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <div>
                      <span className="text-xs font-bold text-slate-900">{sc.name}</span>
                      <span className="mr-2 text-[10px] text-slate-400">({sc.scenario_type})</span>
                    </div>
                    <span className="text-[11px] text-slate-500">أفق التوقع: {sc.target_horizon_months} شهر</span>
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
                    <div>
                      <span className="text-slate-400 block text-[10px]">استثمار مطلوب (CAPEX):</span>
                      <span className="font-bold text-slate-800">{sc.capex_required ? `${sc.capex_required.toLocaleString()} ر.س` : "—"}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">مصاريف إضافية (OPEX):</span>
                      <span className="font-bold text-slate-800">{sc.additional_monthly_opex ? `${sc.additional_monthly_opex.toLocaleString()} ر.س` : "—"}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">إيراد إضافي متوقع:</span>
                      <span className="font-bold text-slate-800">{sc.expected_monthly_revenue_uplift ? `${sc.expected_monthly_revenue_uplift.toLocaleString()} ر.س` : "—"}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px]">زيادة الطاقة الاستيعابية:</span>
                      <span className="font-bold text-slate-800">{sc.target_capacity_increase_pct ? `${sc.target_capacity_increase_pct}%` : "—"}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 6: WHAT-IF SCENARIOS */}
      {subTab === "what_if" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="border-b border-slate-100 pb-4">
              <h3 className="text-lg font-bold text-slate-900">محاكاة سيناريوهات التوسع (What-If Analysis)</h3>
              <p className="mt-1 text-xs text-slate-500">
                محاكاة مالية شفافة تفصل بين البيانات الفعلية (ACTUAL)، وافتراضات المستخدم (USER_ASSUMPTION)، والمشتقات الحسابية (PLATFORM_DERIVED).
              </p>
            </div>

            {/* Run What-If Form */}
            <form onSubmit={handleRunWhatIf} className="mt-6 rounded-xl bg-slate-50 p-4 border border-slate-200 space-y-4">
              <h4 className="text-xs font-bold text-slate-800">تشغيل محاكاة جديدة</h4>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">اسم المحاكاة</label>
                  <input
                    type="text"
                    required
                    value={whatIfName}
                    onChange={(e) => setWhatIfName(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">أفق المحاكاة (بالأشهر)</label>
                  <input
                    type="number"
                    min="1"
                    max="60"
                    value={whatIfHorizon}
                    onChange={(e) => setWhatIfHorizon(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">رأس المال المطلوب (CAPEX)</label>
                  <input
                    type="number"
                    min="0"
                    value={whatIfCapex}
                    onChange={(e) => setWhatIfCapex(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="ر.س"
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">مصاريف شهرية إضافية (OPEX)</label>
                  <input
                    type="number"
                    min="0"
                    value={whatIfOpex}
                    onChange={(e) => setWhatIfOpex(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="ر.س / شهر"
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">إيراد شهري إضافي متوقع</label>
                  <input
                    type="number"
                    min="0"
                    value={whatIfRevenue}
                    onChange={(e) => setWhatIfRevenue(e.target.value === "" ? "" : Number(e.target.value))}
                    placeholder="ر.س / شهر"
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={runningWhatIf}
                className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {runningWhatIf ? "جارٍ الحساب والمحاكاة..." : "تشغيل المحاكاة"}
              </button>
            </form>

            {/* List What-If Models */}
            <div className="mt-6 space-y-4">
              <h4 className="text-xs font-bold text-slate-800">نتائج المحاكاة السابقة ({data.what_if_models.length})</h4>
              {data.what_if_models.map((m) => (
                <div key={m.id} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <span className="text-xs font-bold text-slate-900">{m.scenario_name}</span>
                    <span className="text-[11px] text-slate-500">
                      {m.created_at ? new Date(m.created_at).toLocaleDateString("ar-SA") : ""}
                    </span>
                  </div>

                  <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3 text-xs">
                    <div className="rounded-lg bg-slate-50 p-3">
                      <span className="text-slate-400 block text-[10px]">السيولة النقدية الدنيا المطلوبة:</span>
                      <span className="text-base font-black text-slate-900">
                        {m.minimum_cash_required ? `${m.minimum_cash_required.toLocaleString()} ر.س` : "—"}
                      </span>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3">
                      <span className="text-slate-400 block text-[10px]">فترة استرداد النقد التقديرية:</span>
                      <span className="text-base font-black text-slate-900">
                        {m.estimated_cash_payback_months ? `${m.estimated_cash_payback_months} شهر` : "غير قابلة للاسترداد"}
                      </span>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-3">
                      <span className="text-slate-400 block text-[10px]">الأثر على مدرج السيولة:</span>
                      <span className="text-base font-black text-slate-900">
                        {m.estimated_net_runway_impact_months ? `${m.estimated_net_runway_impact_months} شهر` : "—"}
                      </span>
                    </div>
                  </div>

                  {/* Monthly projections table */}
                  {m.derived_monthly_projections && m.derived_monthly_projections.length > 0 && (
                    <div className="mt-4 overflow-x-auto border border-slate-200 rounded-lg">
                      <table className="min-w-full text-xs text-right">
                        <thead className="bg-slate-50 border-b border-slate-200 text-slate-600">
                          <tr>
                            <th className="p-2">الشهر</th>
                            <th className="p-2">الإيراد المتوقع</th>
                            <th className="p-2">المصاريف المتوقعة</th>
                            <th className="p-2">صافي التدفق الشهري</th>
                            <th className="p-2">الرصيد التراكمي</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {m.derived_monthly_projections.slice(0, 12).map((p: any, idx: number) => (
                            <tr key={idx}>
                              <td className="p-2 font-bold">{p.period_label || `M${p.month}`}</td>
                              <td className="p-2 text-emerald-700">{p.projected_revenue?.toLocaleString()} ر.س</td>
                              <td className="p-2 text-red-700">{p.projected_opex?.toLocaleString()} ر.س</td>
                              <td className="p-2 font-bold">{p.projected_net_cash_flow?.toLocaleString()} ر.س</td>
                              <td className="p-2">{p.cumulative_cash_balance?.toLocaleString()} ر.س</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 7: GROWTH FUNDING CONTEXT */}
      {subTab === "funding" && (() => {
        // When a specific scenario is chosen: MUST show ONLY that scenario's context. Never fall back to default or stale numbers.
        const isScenarioMode = Boolean(fundingScenarioId);
        const effectiveFunding: any = isScenarioMode ? scenarioFunding : growth_funding;
        const invNeed = effectiveFunding?.growth_investment_need?.amount;
        const availCash = effectiveFunding?.current_available_cash?.amount;
        const ownerEq = effectiveFunding?.confirmed_funding?.owner_equity;
        const confFac = effectiveFunding?.confirmed_funding?.confirmed_credit_facilities;
        const totConf = effectiveFunding?.confirmed_funding?.total_confirmed;
        const gapStatus = effectiveFunding?.funding_gap_status || effectiveFunding?.funding_gap?.status || "NOT_AVAILABLE";
        const gapAmt = effectiveFunding?.funding_gap?.gap_amount;
        const unknowns = effectiveFunding?.unknown_components || [];

        return (
          <div className="space-y-6" data-testid="growth-funding-section">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="border-b border-slate-100 pb-4">
                <h3 className="text-lg font-bold text-slate-900">سياق التمويل للنمو (Growth Funding Context)</h3>
                <p className="mt-1 text-xs text-slate-500">
                  ربط مباشر وموثوق مع برامج التمويل المعتمدة في Wave 2 دون تكرار منطق المطابقة، وتحديد الفجوة التمويلية لكل سيناريو توسع.
                </p>
              </div>

              {/* Strict Governance Disclaimer */}
              {effectiveFunding?.disclaimer_ar && (
                <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-xs font-semibold text-amber-900">
                  ⚠️ {effectiveFunding.disclaimer_ar}
                </div>
              )}

              {/* Scenario Selector */}
              <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50/60 p-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <label htmlFor="funding-scenario-select" className="text-xs font-bold text-blue-950 block">
                      اختيار سيناريو النمو المستهدف لتقييم الاحتياج التمويلي:
                    </label>
                    <p className="text-[11px] text-blue-800 mt-0.5">
                      اختر سيناريو محفوظاً لحساب الاحتياج الاستثماري والفجوة التمويلية ومطابقة التمويل الخاصة به
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      id="funding-scenario-select"
                      aria-label="اختيار سيناريو النمو المستهدف"
                      value={fundingScenarioId ?? ""}
                      onChange={(e) => handleScenarioFundingChange(e.target.value ? Number(e.target.value) : null)}
                      className="rounded-lg border border-blue-300 bg-white px-3 py-2 text-xs font-medium text-slate-800 shadow-sm focus:border-blue-500 focus:outline-none"
                    >
                      <option value="">(الوضع الافتراضي / بدون سيناريو مخصص)</option>
                      {data.scenarios.map((scen) => (
                        <option key={scen.id} value={scen.id}>
                          {scen.name} — الاستثمار: {scen.capex_required != null ? formatSAR(scen.capex_required) : "غير محدد"}
                        </option>
                      ))}
                    </select>
                    {loadingFunding && (
                      <span className="text-xs font-bold text-blue-700 animate-pulse">جارٍ التحديث...</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Loading State for Scenario Switch */}
              {loadingFunding && (
                <div className="mt-6 flex min-h-[140px] items-center justify-center rounded-xl border border-blue-100 bg-blue-50/30">
                  <div className="flex items-center gap-3">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
                    <span className="text-xs font-semibold text-blue-900">
                      جارٍ جلب سياق التمويل الدقيق للسيناريو المحدد...
                    </span>
                  </div>
                </div>
              )}

              {/* Explicit Error / Unavailable State */}
              {!loadingFunding && fundingError && isScenarioMode && (
                <div className="mt-6 rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-800" role="alert" data-testid="funding-scenario-error">
                  <p className="font-bold">⚠️ تعذر استرجاع بيانات التمويل للسيناريو المحدد:</p>
                  <p className="mt-1">{fundingError}</p>
                  <p className="mt-2 text-[11px] text-red-600">
                    تم إيقاف عرض أرقام السيناريو السابق منعاً لعرض بيانات مضللة أو قديمة (Stale Context).
                  </p>
                </div>
              )}

              {/* Empty / Not Found Scenario State */}
              {!loadingFunding && !fundingError && isScenarioMode && !scenarioFunding && (
                <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-6 text-center text-xs text-slate-600">
                  بيانات التمويل لهذا السيناريو غير متوفرة حالياً.
                </div>
              )}

              {/* Scenario Context or Default Context Details */}
              {!loadingFunding && !fundingError && effectiveFunding && (
                <>
                  {/* Unknown Components Alert Banner */}
                  {unknowns.length > 0 && (
                    <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                      <span className="font-bold">⚠️ بنود تمويلية مجهولة (Unknown Components): </span>
                      <span>توجد عناصر تمويلية غير مسجلة تمنع احتساب الفجوة التمويلية بشكل نهائي: </span>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {unknowns.map((u: string, idx: number) => {
                          const labels: Record<string, string> = {
                            cash_on_hand: "السيولة النقدية المتاحة (cash_on_hand)",
                            owner_equity: "مساهمة المالك (owner_equity)",
                            confirmed_facilities: "التسهيلات المعتمدة (confirmed_facilities)",
                            growth_investment: "الاستثمار المطلوب للسيناريو (growth_investment)",
                          };
                          return (
                            <span key={idx} className="rounded-md bg-amber-200/80 px-2 py-0.5 text-[11px] font-semibold text-amber-950">
                              {labels[u] || u}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* 4 Funding Key Metrics Cards */}
                  <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    {/* 1. Growth Investment Need */}
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-slate-500">الاحتياج الاستثماري للتوسع</span>
                        <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">
                          {effectiveFunding.growth_investment_need?.status || "UNKNOWN"}
                        </span>
                      </div>
                      <p className="mt-2 text-lg font-bold text-slate-900">
                        {invNeed != null ? formatSAR(invNeed) : "مجهول / غير محدد"}
                      </p>
                      <p className="mt-1 text-[10px] text-slate-500 truncate">
                        {effectiveFunding.growth_investment_need?.source || "حدد سيناريو"}
                      </p>
                    </div>

                    {/* 2. Actual Available Cash */}
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-slate-500">السيولة النقدية الفعلية</span>
                        <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">
                          {effectiveFunding.current_available_cash?.status || "UNKNOWN"}
                        </span>
                      </div>
                      <p className="mt-2 text-lg font-bold text-slate-900">
                        {availCash != null ? formatSAR(availCash) : "غير متوفرة"}
                      </p>
                      <p className="mt-1 text-[10px] text-slate-500 truncate">
                        {effectiveFunding.current_available_cash?.source || "آخر دورة فعلية"}
                      </p>
                    </div>

                    {/* 3. Confirmed Funding */}
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-slate-500">التمويل المؤكد المتاح</span>
                        <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700">
                          {effectiveFunding.confirmed_funding?.status || "UNKNOWN"}
                        </span>
                      </div>
                      <p className="mt-2 text-lg font-bold text-slate-900">
                        {totConf != null ? formatSAR(totConf) : "مجهول"}
                      </p>
                      <p className="mt-1 text-[10px] text-slate-500">
                        {ownerEq != null ? `رأس مال: ${formatSAR(ownerEq)}` : "رأس مال: مجهول"}
                        {" • "}
                        {confFac != null ? `تسهيلات: ${formatSAR(confFac)}` : "تسهيلات: مجهول"}
                      </p>
                    </div>

                    {/* 4. Funding Gap */}
                    <div className={`rounded-xl border p-4 ${gapStatus === "CALCULATED" ? (gapAmt === 0 ? "border-emerald-200 bg-emerald-50/60" : "border-red-200 bg-red-50/60") : "border-slate-200 bg-slate-50"}`}>
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold text-slate-500">الفجوة التمويلية (Funding Gap)</span>
                        <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${gapStatus === "CALCULATED" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>
                          {gapStatus}
                        </span>
                      </div>
                      <p className={`mt-2 text-lg font-bold ${gapStatus === "CALCULATED" && gapAmt != null ? (gapAmt === 0 ? "text-emerald-800" : "text-red-700") : "text-slate-600"}`}>
                        {gapStatus === "CALCULATED" && gapAmt != null ? formatSAR(gapAmt) : "غير متاحة / يلزم بيانات"}
                      </p>
                      <p className="mt-1 text-[10px] text-slate-500 truncate">
                        {gapStatus === "CALCULATED" && gapAmt === 0 ? "التمويل المتاح يغطي متطلبات السيناريو" : (gapStatus === "CALCULATED" ? "عجز تمويلي يتطلب تغطية إضافية" : "مجهولة لوجود مدخلات ناقصة")}
                      </p>
                    </div>
                  </div>

                  {/* Wave 2 Matched Programs */}
                  <div className="mt-8">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-slate-800">
                        البرامج التمويلية المتطابقة (من محرك Wave 2): {effectiveFunding.wave2_matched_programs_count}
                      </h4>
                      <span className="text-[11px] text-slate-500 font-medium">
                        حالات المطابقة مثبتة بدقة وتخضع للاشتراطات الرسمية
                      </span>
                    </div>
                    <div className="mt-3 space-y-3">
                      {effectiveFunding.wave2_matched_programs && effectiveFunding.wave2_matched_programs.length > 0 ? (
                        effectiveFunding.wave2_matched_programs.map((p: any, idx: number) => {
                          const fitColors: Record<string, string> = {
                            MATCH: "bg-emerald-50 text-emerald-800 border-emerald-200",
                            POSSIBLE_MATCH: "bg-blue-50 text-blue-800 border-blue-200",
                            NEEDS_INFORMATION: "bg-amber-50 text-amber-800 border-amber-200",
                            NOT_MATCHED: "bg-slate-50 text-slate-600 border-slate-200",
                            NOT_EVALUATED: "bg-slate-50 text-slate-500 border-slate-200",
                          };
                          return (
                            <div key={idx} className="rounded-xl border border-slate-200 bg-white p-4">
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-slate-900">{p.program_name_ar}</span>
                                <span className={`rounded-lg border px-2 py-0.5 text-[10px] font-bold ${fitColors[p.fit_status] || "bg-slate-50 text-slate-700"}`}>
                                  {p.fit_status}
                                </span>
                              </div>
                              <div className="mt-2 text-xs text-slate-600">
                                <span>الجهة الراعية: </span>
                                <span className="font-bold text-slate-800">{p.sponsor_name_ar}</span>
                                <span className="mx-2">•</span>
                                <span>نوع التمويل: </span>
                                <span className="font-bold text-slate-800">{p.funding_type}</span>
                                {p.status_reason_ar && (
                                  <>
                                    <span className="mx-2">•</span>
                                    <span className="text-slate-500">{p.status_reason_ar}</span>
                                  </>
                                )}
                              </div>
                            </div>
                          );
                        })
                      ) : (
                        <div className="rounded-xl border border-slate-200 bg-slate-50 p-6 text-center text-xs text-slate-500">
                          لا توجد برامج تمويلية متطابقة مع المعطيات الحالية للسيناريو.
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        );
      })()}

      {/* SUB-TAB 8: MONTHLY REVIEWS */}
      {subTab === "reviews" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="border-b border-slate-100 pb-4">
              <h3 className="text-lg font-bold text-slate-900">المراجعة التشغيلية الشهرية (Monthly Business Reviews)</h3>
              <p className="mt-1 text-xs text-slate-500">
                تجميد لقطة تاريخية غير قابلة للتعديل لكل دورة تشغيلية لمقارنة الأداء والوفاء بالأهداف.
              </p>
            </div>

            {/* Create Review Form */}
            <form onSubmit={handleCreateReview} className="mt-6 rounded-xl bg-slate-50 p-4 border border-slate-200 space-y-4">
              <h4 className="text-xs font-bold text-slate-800">تجميد مراجعة دورة تشغيلية</h4>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">رمز الدورة</label>
                  <input
                    type="text"
                    required
                    value={reviewPeriod}
                    onChange={(e) => setReviewPeriod(e.target.value)}
                    placeholder="مثال: 2026-M01 أو M01"
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">المستهدف للدورة القادمة</label>
                  <input
                    type="text"
                    value={reviewTargetNext}
                    onChange={(e) => setReviewTargetNext(e.target.value)}
                    placeholder="مثال: تحقيق إيراد 85,000 ر.س وخفض الهدر"
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">ملاحظات وقرارات المراجعة</label>
                  <input
                    type="text"
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="ملخص تقييم الدورة"
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={submittingReview}
                className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {submittingReview ? "جارٍ التجميد..." : "تجميد المراجعة"}
              </button>
            </form>

            {/* List Reviews */}
            <div className="mt-6 space-y-4">
              <h4 className="text-xs font-bold text-slate-800">سجل المراجعات الشهرية المجمدة ({data.monthly_reviews.length})</h4>
              {data.monthly_reviews.map((r) => (
                <div key={r.id} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <div>
                      <span className="text-xs font-bold text-slate-900">دورة: {r.review_period}</span>
                      <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-700">
                        الإصدار v{r.review_version}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500">
                      {r.created_at ? new Date(r.created_at).toLocaleDateString("ar-SA") : ""}
                    </span>
                  </div>
                  {r.review_notes && <p className="mt-2 text-xs text-slate-700">{r.review_notes}</p>}
                  {r.target_next_month && (
                    <p className="mt-1 text-xs text-emerald-800 font-medium">
                      المستهدف القادم: {r.target_next_month}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 9: DECISIONS & ACTION PLAN */}
      {subTab === "decisions" && (
        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="border-b border-slate-100 pb-4">
              <h3 className="text-lg font-bold text-slate-900">القرار الاستراتيجي وخطة العمل (Strategic Decision & Actions)</h3>
              <p className="mt-1 text-xs text-slate-500">
                حوكمة قرارات (SCALE / FIX / PIVOT / HOLD / STOP). قرار التوسع مقيد بجاهزية السيولة والكفاءة، وقرار تعديل المسار يربط بدورة تحقق جديدة.
              </p>
            </div>

            {/* Expansion Readiness State */}
            <div className="mt-4 rounded-xl bg-slate-50 p-4 border border-slate-200">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700">تقييم الجاهزية للتوسع:</span>
                <span className={`rounded-lg border px-2.5 py-1 text-xs font-bold ${readinessMap[expansion_readiness.readiness_state]?.badge}`}>
                  {readinessMap[expansion_readiness.readiness_state]?.ar || expansion_readiness.readiness_state}
                </span>
              </div>
              <p className="mt-2 text-xs text-slate-600">{expansion_readiness.summary_ar}</p>

              <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                {expansion_readiness.prerequisites.map((p, idx) => (
                  <div key={idx} className="flex items-center justify-between rounded-lg bg-white p-2 text-xs border border-slate-200">
                    <span className="font-bold text-slate-700">{p.name_ar}</span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                        p.status === "PASS"
                          ? "bg-emerald-100 text-emerald-800"
                          : p.status === "FAIL"
                          ? "bg-red-100 text-red-800"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {p.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Record Decision Form */}
            <form onSubmit={handleRecordDecision} className="mt-6 rounded-xl bg-slate-50 p-4 border border-slate-200 space-y-4">
              <h4 className="text-xs font-bold text-slate-800">اعتماد وتثبيت قرار استراتيجي جديد</h4>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">القرار الاستراتيجي</label>
                  <select
                    value={decisionType}
                    onChange={(e) => setDecisionType(e.target.value as any)}
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none font-bold"
                  >
                    <option value="HOLD">تريث وتثبيت الأداء (HOLD)</option>
                    <option value="SCALE">توسع ونمو (SCALE) — مقيد بجاهزية السيولة والاستقرار</option>
                    <option value="FIX">معالجة وتصحيح تشغيلي (FIX)</option>
                    <option value="PIVOT">تعديل المسار (PIVOT) — يطلق دورة تحقق ميداني جديدة</option>
                    <option value="STOP">إيقاف النشاط (STOP) — يحفظ الأرشيف الكامل</option>
                    <option value="NEEDS_INFORMATION">طلب استكمال البيانات (NEEDS_INFORMATION)</option>
                  </select>
                </div>
                <div>
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">تاريخ إعادة التقييم (اختياري)</label>
                  <input
                    type="date"
                    value={decisionReEvalDate}
                    onChange={(e) => setDecisionReEvalDate(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                {decisionType === "SCALE" && (
                  <div className="sm:col-span-2">
                    <label className="text-[11px] font-bold text-slate-600 block mb-1">
                      سيناريو التوسع المعتمد (إلزامي لقرار SCALE)
                    </label>
                    <select
                      required
                      value={decisionScenarioId}
                      onChange={(e) => setDecisionScenarioId(e.target.value ? Number(e.target.value) : "")}
                      className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none font-bold"
                    >
                      <option value="">-- اختر سيناريو التوسع المعتمد لمعرفة الاحتياج الاستثماري --</option>
                      {(data.scenarios || []).map((s: any) => (
                        <option key={s.id} value={s.id}>
                          {s.title} ({s.investment_required ? `${s.investment_required.toLocaleString()} ر.س` : "بدون متطلب استثماري"})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="sm:col-span-2">
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">مبررات القرار (إلزامي)</label>
                  <textarea
                    required
                    rows={3}
                    value={decisionReason}
                    onChange={(e) => setDecisionReason(e.target.value)}
                    placeholder="دوّن المبررات المستندة للبيانات والوقائع الفعلية..."
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-[11px] font-bold text-slate-600 block mb-1">شروط التنفيذ (سطر لكل شرط)</label>
                  <textarea
                    rows={2}
                    value={decisionConditions}
                    onChange={(e) => setDecisionConditions(e.target.value)}
                    placeholder="مثال: تحقيق ربحية تشغيلية لشهرين متتاليين..."
                    className="w-full rounded-xl border border-slate-300 p-2.5 text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={submittingDecision}
                className="rounded-xl bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                {submittingDecision ? "جارٍ التحقق والاعتماد..." : "تأكيد واعتماد القرار"}
              </button>
            </form>

            {/* Decisions History */}
            <div className="mt-6 space-y-4">
              <h4 className="text-xs font-bold text-slate-800">سجل القرارات المعتمدة ({data.decisions.length})</h4>
              {data.decisions.map((dec) => (
                <div key={dec.id} className="rounded-xl border border-slate-200 bg-white p-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-2">
                    <div>
                      <span className="text-xs font-black text-slate-900">قرار: {dec.decision}</span>
                      <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-700">
                        إصدار v{dec.decision_version}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500">
                      {dec.decided_at ? new Date(dec.decided_at).toLocaleDateString("ar-SA") : ""}
                    </span>
                  </div>
                  {dec.pivot_validation_workspace_id && (
                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-purple-50 p-3 text-xs border border-purple-200">
                      <div>
                        <span className="font-bold text-purple-950 block">
                          🔗 تم ربط دورة تحقق ميداني جديدة (Wave 4 Workspace ID: {dec.pivot_validation_workspace_id})
                        </span>
                        <span className="text-[11px] text-purple-800">
                          تم إنشاء فرضية تعديل المسار وبدء دورة اختبارات وأدلة ميدانية مستقلة
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          if (onNavigateTab) {
                            onNavigateTab("validation", dec.pivot_validation_workspace_id ?? undefined);
                          } else {
                            window.location.hash = "#validation";
                          }
                        }}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-purple-700 px-3.5 py-1.5 text-xs font-bold text-white shadow-sm hover:bg-purple-800 transition-colors cursor-pointer"
                      >
                        الانتقال إلى دورة التحقق الميداني الجديدة (Wave 4) ↗
                      </button>
                    </div>
                  )}
                  {dec.recommended_next_actions && dec.recommended_next_actions.length > 0 && (
                    <div className="mt-3">
                      <span className="text-[11px] font-bold text-slate-500 block mb-1">الإجراءات الموصى بها:</span>
                      <ul className="list-disc list-inside text-xs text-slate-700 space-y-0.5">
                        {dec.recommended_next_actions.map((act, i) => (
                          <li key={i}>{act}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Action Plan Management */}
            <div className="mt-8 border-t border-slate-200 pt-6">
              <div className="flex items-center justify-between mb-4">
                <h4 className="text-xs font-bold text-slate-800">خطة العمل التشغيلية (Action Plan)</h4>
                <span className="text-[11px] text-slate-500">إجمالي البنود: {data.actions.length}</span>
              </div>

              {/* Add Action */}
              <form onSubmit={handleCreateAction} className="flex gap-2 mb-4">
                <input
                  type="text"
                  required
                  value={newActionTitle}
                  onChange={(e) => setNewActionTitle(e.target.value)}
                  placeholder="أضف بند عمل تنفيذي أو تصحيحي..."
                  className="flex-1 rounded-xl border border-slate-300 p-2 text-xs focus:border-emerald-500 focus:outline-none"
                />
                <select
                  value={newActionType}
                  onChange={(e) => setNewActionType(e.target.value)}
                  className="rounded-xl border border-slate-300 p-2 text-xs"
                >
                  <option value="REMEDIATION">معالجة (REMEDIATION)</option>
                  <option value="EXPANSION">توسع (EXPANSION)</option>
                  <option value="OPERATIONAL">تشغيلي (OPERATIONAL)</option>
                </select>
                <button
                  type="submit"
                  disabled={submittingAction}
                  className="rounded-xl bg-slate-900 px-4 py-2 text-xs font-bold text-white hover:bg-black disabled:opacity-50"
                >
                  إضافة
                </button>
              </form>

              {/* Action items list */}
              <div className="space-y-2">
                {data.actions.map((act) => (
                  <div
                    key={act.id}
                    className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-3 text-xs"
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={act.status === "COMPLETED"}
                        onChange={() => handleToggleActionStatus(act.id, act.status)}
                        className="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                      />
                      <span className={act.status === "COMPLETED" ? "line-through text-slate-400" : "font-medium text-slate-800"}>
                        {act.title}
                      </span>
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-600">
                        {act.action_type}
                      </span>
                    </div>
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                        act.status === "COMPLETED"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {act.status === "COMPLETED" ? "مكتمل" : "قيد المتابعة"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
