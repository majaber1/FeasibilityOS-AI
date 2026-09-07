"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getValidationWorkspace,
  getValidationWorkspaceById,
  getValidationCycles,
  addValidationHypothesis,
  updateValidationHypothesis,
  addValidationExperiment,
  updateValidationExperiment,
  recordValidationEvidence,
  recordValidationDecision,
  getValidationDecisions,
  type ValidationWorkspaceData,
  type ValidationHypothesis,
  type ValidationExperiment,
  type ValidationEvidenceItem,
  type ValidationDecisionItem,
} from "@/lib/api";

const hypothesisTypes = [
  { value: "CUSTOMER_PROBLEM", ar: "مشكلة العميل المستهدف", en: "Customer Problem" },
  { value: "DEMAND", ar: "الطلب الفعلي في السوق", en: "Market Demand" },
  { value: "WILLINGNESS_TO_PAY", ar: "الاستعداد للدفع والتسعير", en: "Willingness to Pay" },
  { value: "DELIVERY_OR_OPERATIONS", ar: "القدرة التشغيلية والتوريد", en: "Operations & Delivery" },
  { value: "REGULATORY_OR_LOCATION", ar: "الموقع والاشتراطات التنظيمية", en: "Location & Regulatory" },
];

const experimentTypes = [
  { value: "INTERVIEW", ar: "مقابلات شخصية مع العملاء", en: "Customer Interviews" },
  { value: "SURVEY", ar: "استبيان استطلاعي رقمي", en: "Market Survey" },
  { value: "WAITLIST_LANDING_PAGE", ar: "صفحة هبوط / قائمة انتظار", en: "Waitlist / Landing Page" },
  { value: "PRICE_TEST", ar: "اختبار حساسية السعر", en: "Price Sensitivity Test" },
  { value: "COMPETITOR_OBSERVATION", ar: "رصد ميداني ومقارنة منافسين", en: "Competitor Field Observation" },
];

const evidenceTypes = [
  { value: "CUSTOMER_INTERVIEW", ar: "مقابلة عميل موثقة", en: "Customer Interview" },
  { value: "SURVEY_RESULT", ar: "نتائج استبيان ميداني", en: "Survey Result" },
  { value: "DEMAND_SIGNAL", ar: "إشارة طلب / تسجيلات حقيقية", en: "Demand Signal" },
  { value: "PRICING_TEST", ar: "أدلة اختبار التسعير", en: "Pricing Test" },
  { value: "COMPETITOR_BENCHMARK", ar: "بيانات منافس مرصودة", en: "Competitor Benchmark" },
];

const statusLabels: Record<string, { ar: string; color: string }> = {
  NEEDS_EVIDENCE: { ar: "بحاجة لأدلة ميدانية", color: "bg-amber-100 text-amber-800 border-amber-300" },
  IN_PROGRESS: { ar: "التحقق جاري", color: "bg-blue-100 text-blue-800 border-blue-300" },
  PARTIALLY_VALIDATED: { ar: "متحقق جزئياً", color: "bg-purple-100 text-purple-800 border-purple-300" },
  VALIDATED: { ar: "تم التحقق بنجاح", color: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  NOT_VALIDATED: { ar: "لم يتم التحقق (افتراضات مرفوضة)", color: "bg-red-100 text-red-800 border-red-300" },
  UNTESTED: { ar: "قيد الانتظار (لم تُختبر)", color: "bg-slate-100 text-slate-700 border-slate-300" },
  TESTING: { ar: "جارٍ الاختبار", color: "bg-blue-100 text-blue-700 border-blue-300" },
  SUPPORTED: { ar: "مدعومة بالأدلة", color: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  NOT_SUPPORTED: { ar: "مرفوضة / غير مدعومة", color: "bg-red-100 text-red-800 border-red-300" },
  INCONCLUSIVE: { ar: "غير حاسمة", color: "bg-amber-100 text-amber-800 border-amber-300" },
  PLANNED: { ar: "مخططة", color: "bg-slate-100 text-slate-700 border-slate-300" },
  RUNNING: { ar: "قيد التنفيذ", color: "bg-blue-100 text-blue-700 border-blue-300" },
  COMPLETED: { ar: "مكتملة", color: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  CANCELLED: { ar: "ملغاة", color: "bg-slate-100 text-slate-500 border-slate-200" },
};

const decisionLabels: Record<string, { ar: string; color: string; desc: string }> = {
  GO: {
    ar: "انطلاق كامل (GO)",
    color: "bg-emerald-600 text-white hover:bg-emerald-700",
    desc: "الفرضيات الجوهرية مدعومة بأدلة كافية للانتقال إلى خطة الإطلاق والتشغيل.",
  },
  GO_WITH_CONDITIONS: {
    ar: "انطلاق بشروط (GO WITH CONDITIONS)",
    color: "bg-blue-600 text-white hover:bg-blue-700",
    desc: "الانطلاق مع اشتراط تنفيذ متطلبات محددة أو ضوابط حذر.",
  },
  PIVOT: {
    ar: "تعديل المسار (PIVOT)",
    color: "bg-amber-600 text-white hover:bg-amber-700",
    desc: "الافتراضات الأساسية لم تتطابق مع السوق، ويلزم تعديل نموذج العمل أو المنتج.",
  },
  STOP: {
    ar: "إيقاف المشروع (STOP)",
    color: "bg-red-600 text-white hover:bg-red-700",
    desc: "الأدلة تثبت عدم جدوى الاستمرار لتفادي استنزاف رأس المال.",
  },
};

export default function ValidationTab({
  studyId,
  token,
  locale = "ar",
}: {
  studyId: number;
  token: string;
  locale?: "ar" | "en";
}) {
  const ar = locale === "ar";
  const [workspace, setWorkspace] = useState<ValidationWorkspaceData | null>(null);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<number | null>(null);
  const [cycles, setCycles] = useState<any[]>([]);
  const [decisions, setDecisions] = useState<ValidationDecisionItem[]>([]);
  const [subTab, setSubTab] = useState<"hypotheses" | "experiments" | "evidence" | "decision">("hypotheses");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Forms states
  const [showHypothesisModal, setShowHypothesisModal] = useState(false);
  const [newHypoType, setNewHypoType] = useState("CUSTOMER_PROBLEM");
  const [newHypoStatement, setNewHypoStatement] = useState("");
  const [newHypoImportance, setNewHypoImportance] = useState("CRITICAL");
  const [newHypoRationale, setNewHypoRationale] = useState("");

  const [showExpModal, setShowExpModal] = useState(false);
  const [newExpType, setNewExpType] = useState("INTERVIEW");
  const [newExpTitle, setNewExpTitle] = useState("");
  const [newExpObj, setNewExpObj] = useState("");
  const [newExpMethod, setNewExpMethod] = useState("");
  const [newExpCriteria, setNewExpCriteria] = useState("");
  const [newExpHypoId, setNewExpHypoId] = useState<number | undefined>(undefined);
  const [newExpSampleSize, setNewExpSampleSize] = useState<number | undefined>(undefined);

  const [showEvidenceModal, setShowEvidenceModal] = useState(false);
  const [newEvType, setNewEvType] = useState("CUSTOMER_INTERVIEW");
  const [newEvTitle, setNewEvTitle] = useState("");
  const [newEvHypoId, setNewEvHypoId] = useState<number | undefined>(undefined);
  const [newEvExpId, setNewEvExpId] = useState<number | undefined>(undefined);
  const [newEvStrength, setNewEvStrength] = useState<"STRONG" | "MODERATE" | "WEAK">("MODERATE");
  const [newEvDirection, setNewEvDirection] = useState<"SUPPORTING" | "REFUTING" | "NEUTRAL" | "">("");
  const [newEvSimulated, setNewEvSimulated] = useState(false);
  const [newEvNotes, setNewEvNotes] = useState("");
  const [evInterviewRole, setEvInterviewRole] = useState("");
  const [evInterviewQuote, setEvInterviewQuote] = useState("");
  const [evSurveyResponses, setEvSurveyResponses] = useState<number | "">("");
  const [evSurveyAgreed, setEvSurveyAgreed] = useState<number | "">("");
  const [evDemandImpressions, setEvDemandImpressions] = useState<number | "">("");
  const [evDemandLeads, setEvDemandLeads] = useState<number | "">("");
  const [evAssumedPrice, setEvAssumedPrice] = useState<number | "">("");
  const [evTestedPrice, setEvTestedPrice] = useState<number | "">("");
  const [evCompetitorName, setEvCompetitorName] = useState("");
  const [evCompetitorUrl, setEvCompetitorUrl] = useState("");

  const [selectedDecision, setSelectedDecision] = useState<"GO" | "GO_WITH_CONDITIONS" | "PIVOT" | "STOP">("GO");
  const [decisionReason, setDecisionReason] = useState("");
  const [decisionConditions, setDecisionConditions] = useState<string[]>([""]);

  const loadData = useCallback(async (targetWorkspaceId?: number | null) => {
    try {
      setLoading(true);
      setError(null);
      const wid = targetWorkspaceId !== undefined ? targetWorkspaceId : selectedWorkspaceId;
      const ws = wid ? await getValidationWorkspaceById(token, wid) : await getValidationWorkspace(token, studyId);
      setWorkspace(ws);
      if (ws?.id) {
        const decList = await getValidationDecisions(token, ws.id);
        setDecisions(decList);
      }
      try {
        const cycleList = await getValidationCycles(token, studyId);
        setCycles(cycleList.cycles || []);
      } catch {
        // non-blocking
      }
    } catch (err: any) {
      setError(err?.message || "فشل تحميل بيانات التحقق الميداني");
    } finally {
      setLoading(false);
    }
  }, [studyId, token, selectedWorkspaceId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAddHypothesis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspace) return;
    try {
      setError(null);
      await addValidationHypothesis(token, workspace.id, {
        hypothesis_type: newHypoType,
        statement: newHypoStatement,
        importance: newHypoImportance,
        rationale: newHypoRationale,
      });
      setShowHypothesisModal(false);
      setNewHypoStatement("");
      setNewHypoRationale("");
      setActionSuccess(ar ? "تمت إضافة الفرضية بنجاح" : "Hypothesis added successfully");
      await loadData();
    } catch (err: any) {
      setError(err?.message || "فشل إضافة الفرضية");
    }
  };

  const handleUpdateHypoStatus = async (hypoId: number, status: string) => {
    try {
      setError(null);
      await updateValidationHypothesis(token, hypoId, { status });
      setActionSuccess(ar ? "تم تحديث حالة الفرضية" : "Hypothesis status updated");
      await loadData();
    } catch (err: any) {
      setError(err?.message || "تعذر تحديث الفرضية (تأكد من وجود أدلة كافية)");
    }
  };

  const handleAddExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspace) return;
    try {
      setError(null);
      await addValidationExperiment(token, workspace.id, {
        experiment_type: newExpType,
        title: newExpTitle,
        objective: newExpObj,
        method: newExpMethod,
        success_criteria: newExpCriteria,
        hypothesis_id: newExpHypoId || null,
        planned_sample_size: newExpSampleSize || null,
      });
      setShowExpModal(false);
      setNewExpTitle("");
      setNewExpObj("");
      setNewExpMethod("");
      setNewExpCriteria("");
      setActionSuccess(ar ? "تمت إضافة التجربة بنجاح" : "Experiment added successfully");
      await loadData();
    } catch (err: any) {
      setError(err?.message || "فشل إضافة التجربة");
    }
  };

  const handleUpdateExpStatus = async (expId: number, status: string) => {
    try {
      setError(null);
      await updateValidationExperiment(token, expId, { status });
      setActionSuccess(ar ? "تم تحديث حالة التجربة" : "Experiment status updated");
      await loadData();
    } catch (err: any) {
      setError(err?.message || "تعذر تحديث التجربة");
    }
  };

  const handleRecordEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspace) return;
    try {
      setError(null);
      const payload: Record<string, any> = {};
      if (newEvType === "CUSTOMER_INTERVIEW") {
        payload.interviewee_role = evInterviewRole;
        payload.key_quote = evInterviewQuote;
      } else if (newEvType === "SURVEY_RESULT") {
        payload.responses_count = evSurveyResponses === "" ? null : Number(evSurveyResponses);
        payload.agree_count = evSurveyAgreed === "" ? null : Number(evSurveyAgreed);
      } else if (newEvType === "DEMAND_SIGNAL") {
        payload.sample_size = evDemandImpressions === "" ? null : Number(evDemandImpressions);
        payload.leads_count = evDemandLeads === "" ? null : Number(evDemandLeads);
      } else if (newEvType === "PRICING_TEST") {
        payload.assumed_price = evAssumedPrice === "" ? null : Number(evAssumedPrice);
        payload.tested_willingness_price = evTestedPrice === "" ? null : Number(evTestedPrice);
      } else if (newEvType === "COMPETITOR_BENCHMARK") {
        payload.competitor_name = evCompetitorName;
      }

      if (newEvHypoId && !newEvDirection) {
        setError(ar ? "يجب اختيار أثر الدليل على الفرضية بشكل صريح (يدعم / يدحض / محايد)" : "Please select the evidence direction for the linked hypothesis");
        return;
      }

      if (newEvType === "COMPETITOR_BENCHMARK" && (!evCompetitorUrl || !evCompetitorUrl.trim())) {
        setError(ar ? "أدلة المقارنة التنافسية تتطلب توفير رابط ويب صالح (source_url)" : "Competitor benchmark requires a valid source URL");
        return;
      }

      await recordValidationEvidence(token, workspace.id, {
        evidence_type: newEvType,
        title: newEvTitle,
        hypothesis_id: newEvHypoId || null,
        experiment_id: newEvExpId || null,
        evidence_strength: newEvStrength,
        evidence_direction: newEvDirection ? (newEvDirection as "SUPPORTING" | "REFUTING" | "NEUTRAL") : undefined,
        is_simulated: newEvSimulated,
        source_url: newEvType === "COMPETITOR_BENCHMARK" ? evCompetitorUrl : null,
        notes: newEvNotes,
        structured_payload: payload,
      });

      setShowEvidenceModal(false);
      setNewEvTitle("");
      setNewEvNotes("");
      setNewEvDirection("");
      setNewEvStrength("MODERATE");
      setEvCompetitorUrl("");
      setActionSuccess(ar ? "تم توثيق الدليل الميداني بنجاح" : "Evidence recorded successfully");
      await loadData();
    } catch (err: any) {
      setError(err?.message || "فشل تسجيل الدليل الميداني");
    }
  };

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspace) return;
    try {
      setError(null);
      const cleanConditions = decisionConditions.map((c) => c.trim()).filter(Boolean);
      await recordValidationDecision(token, workspace.id, {
        decision: selectedDecision,
        decision_reason: decisionReason,
        conditions: selectedDecision === "GO_WITH_CONDITIONS" ? cleanConditions : undefined,
      });
      setActionSuccess(ar ? "تم تسجيل قرار التحقق وتجميد نسخة الأدلة بنجاح" : "Validation decision recorded");
      setDecisionReason("");
      await loadData();
    } catch (err: any) {
      setError(err?.message || "فشل تسجيل قرار التحقق");
    }
  };

  if (loading && !workspace) {
    return (
      <div className="flex min-h-[300px] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-600 border-t-transparent"></div>
        <span className="mr-3 text-slate-600">{ar ? "جارٍ تحميل منظومة التحقق الميداني..." : "Loading validation..."}</span>
      </div>
    );
  }

  const evalStatus = workspace?.evaluation?.status || "NEEDS_EVIDENCE";
  const badgeStyle = statusLabels[evalStatus] || { ar: evalStatus, color: "bg-slate-100 text-slate-700" };

  return (
    <div className="space-y-6" data-testid="validation-os-workspace">
      {/* HEADER BANNER */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
                Wave 4 — Evidence-Driven Market Validation OS
              </span>
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                {ar ? "منظومة إثبات الجدوى الميدانية" : "Empirical Validation"}
              </span>
            </div>
            <h2 className="mt-2 text-2xl font-bold text-slate-900">
              {ar ? "التحقق الميداني والافتراضات الحرجة" : "Market Validation & Critical Hypotheses"}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {ar
                ? "إثبات الافتراضات الجوهرية (المشكلة، الطلب، الاستعداد للدفع) عبر أدلة ميدانية حقيقية ومقابلات عملاء قبل استثمار رأس المال."
                : "Validate core business hypotheses with real evidence before capital allocation."}
            </p>
          </div>

          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">{ar ? "دورة التحقق:" : "Cycle:"}</span>
              {(cycles.length > 1 || (workspace?.total_cycles && workspace.total_cycles > 1)) ? (
                <select
                  value={workspace?.id || ""}
                  onChange={(e) => {
                    const id = Number(e.target.value);
                    setSelectedWorkspaceId(id);
                    loadData(id);
                  }}
                  className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs font-semibold text-slate-800 shadow-xs focus:border-brand-500 focus:outline-none"
                  data-testid="validation-cycle-switcher"
                >
                  {cycles.length > 0 ? (
                    cycles.map((c) => (
                      <option key={c.workspace_id} value={c.workspace_id}>
                        {ar ? `الدورة ${c.cycle_number}` : `Cycle ${c.cycle_number}`}
                        {c.is_current ? (ar ? " (الحالية - النشطة)" : " (Current - Active)") : (ar ? " (تاريخية)" : " (Historical)")}
                        {c.latest_decision ? ` · ${c.latest_decision}` : ""}
                      </option>
                    ))
                  ) : (
                    <option value={workspace?.id || ""}>
                      {ar ? `الدورة ${workspace?.cycle_number || 1}` : `Cycle ${workspace?.cycle_number || 1}`}
                    </option>
                  )}
                </select>
              ) : (
                <span className="rounded-md bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-700">
                  {ar ? `الدورة ${workspace?.cycle_number || 1}` : `Cycle ${workspace?.cycle_number || 1}`}
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">{ar ? "حالة التحقق الشاملة:" : "Overall Status:"}</span>
              <span
                className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-bold shadow-sm ${badgeStyle.color}`}
                data-testid="validation-status-badge"
              >
                {ar ? badgeStyle.ar : evalStatus}
              </span>
            </div>
          </div>
        </div>

        {workspace?.is_current_cycle === false && (
          <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900 flex items-center justify-between">
            <span>
              {ar
                ? "⚠️ تنبيه: أنت تستعرض دورة تحقق تاريخية مؤرشفة. تتوفر دورة تحقق حالية نشطة أحدث (ناتجة عن مسار PIVOT)."
                : "⚠️ Note: Viewing an archived historical validation cycle. A newer active cycle is available."}
            </span>
            <button
              onClick={() => {
                setSelectedWorkspaceId(null);
                loadData(null);
              }}
              className="rounded-md bg-amber-200 px-2 py-1 font-semibold text-amber-950 hover:bg-amber-300"
            >
              {ar ? "الانتقال للدورة الحالية" : "Go to Current Cycle"}
            </button>
          </div>
        )}

        {/* SUMMARY & TRANSPARENT METRICS */}
        {workspace?.evaluation && (
          <div className="mt-4">
            <div className="rounded-xl bg-slate-50 p-4 border border-slate-200">
              <p className="text-sm font-medium text-slate-800 leading-relaxed">
                {workspace.evaluation.summary_ar}
              </p>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5 text-center">
              <div className="rounded-xl border border-slate-200 bg-white p-3 shadow-xs">
                <span className="text-xs text-slate-500">{ar ? "إجمالي الفرضيات" : "Total Hypotheses"}</span>
                <p className="mt-1 text-xl font-bold text-slate-900">{workspace.evaluation.total_hypotheses}</p>
              </div>
              <div className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3 shadow-xs">
                <span className="text-xs text-emerald-800 font-medium">{ar ? "الفرضيات الحرجة المدعومة" : "Critical Supported"}</span>
                <p className="mt-1 text-xl font-bold text-emerald-700">
                  {workspace.evaluation.critical_supported} / {workspace.evaluation.critical_total}
                </p>
              </div>
              <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-3 shadow-xs">
                <span className="text-xs text-blue-800 font-medium">{ar ? "فرضيات مدعومة بأدلة" : "Supported"}</span>
                <p className="mt-1 text-xl font-bold text-blue-700">
                  {workspace.evaluation.counts?.SUPPORTED || 0}
                </p>
              </div>
              <div className="rounded-xl border border-red-200 bg-red-50/50 p-3 shadow-xs">
                <span className="text-xs text-red-800 font-medium">{ar ? "فرضيات مرفوضة" : "Not Supported"}</span>
                <p className="mt-1 text-xl font-bold text-red-700">
                  {workspace.evaluation.counts?.NOT_SUPPORTED || 0}
                </p>
              </div>
              <div className="rounded-xl border border-purple-200 bg-purple-50/50 p-3 shadow-xs">
                <span className="text-xs text-purple-800 font-medium">{ar ? "سجل الأدلة المرصودة" : "Recorded Evidence"}</span>
                <p className="mt-1 text-xl font-bold text-purple-700">{workspace.evidence?.length || 0}</p>
              </div>
            </div>
          </div>
        )}

        {/* LATEST DECISION BANNER (IF ANY) */}
        {workspace?.latest_decision && (
          <div className="mt-5 rounded-xl border border-blue-200 bg-blue-50/60 p-4" data-testid="latest-decision-banner">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-xs font-bold text-blue-900">
                {ar ? `القرار الرسمي المعتمد (الإصدار v${workspace.latest_decision.decision_version})` : `Official Decision v${workspace.latest_decision.decision_version}`}
              </span>
              <span className="rounded-full bg-blue-200/80 px-2.5 py-0.5 text-xs font-semibold text-blue-900">
                {workspace.latest_decision.decided_at?.slice(0, 10)}
              </span>
            </div>
            <div className="mt-2 flex items-center gap-3">
              <span className="rounded-md bg-blue-700 px-3 py-1 text-xs font-bold text-white">
                {workspace.latest_decision.decision}
              </span>
              <p className="text-sm font-semibold text-blue-950">{workspace.latest_decision.decision_reason}</p>
            </div>
            {workspace.latest_decision.conditions && workspace.latest_decision.conditions.length > 0 && (
              <div className="mt-2 text-xs text-blue-900">
                <span className="font-bold">{ar ? "الشروط الملزمة:" : "Conditions:"} </span>
                <ul className="list-inside list-disc mt-1 space-y-0.5">
                  {workspace.latest_decision.conditions.map((cond, i) => (
                    <li key={i}>{cond}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ALERT / MESSAGE BANNER */}
      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <p className="font-bold">{ar ? "تنبيه" : "Error"}</p>
          <p className="mt-1">{error}</p>
        </div>
      )}
      {actionSuccess && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          <p>{actionSuccess}</p>
        </div>
      )}

      {/* SUB-TABS NAVIGATION */}
      <div className="flex border-b border-slate-200">
        <button
          onClick={() => setSubTab("hypotheses")}
          className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
            subTab === "hypotheses"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
          data-testid="subtab-hypotheses"
        >
          {ar ? "الفرضيات الحرجة" : "Critical Hypotheses"} ({workspace?.hypotheses?.length || 0})
        </button>
        <button
          onClick={() => setSubTab("experiments")}
          className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
            subTab === "experiments"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
          data-testid="subtab-experiments"
        >
          {ar ? "التجارب الميدانية" : "Field Experiments"} ({workspace?.experiments?.length || 0})
        </button>
        <button
          onClick={() => setSubTab("evidence")}
          className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
            subTab === "evidence"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
          data-testid="subtab-evidence"
        >
          {ar ? "سجل الأدلة الميدانية" : "Evidence Matrix"} ({workspace?.evidence?.length || 0})
        </button>
        <button
          onClick={() => setSubTab("decision")}
          className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
            subTab === "decision"
              ? "border-emerald-600 text-emerald-700 font-bold"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
          data-testid="subtab-decision"
        >
          {ar ? "قرار التحقق والانطلاق" : "Validation Decision"}
        </button>
      </div>

      {/* TAB 1: HYPOTHESES */}
      {subTab === "hypotheses" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-900">
              {ar ? "قائمة الفرضيات الميدانية" : "Validation Hypotheses"}
            </h3>
            <button
              onClick={() => setShowHypothesisModal(true)}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
              data-testid="add-hypothesis-btn"
            >
              {ar ? "+ إضافة فرضية جديدة" : "+ Add Hypothesis"}
            </button>
          </div>

          <div className="grid gap-4">
            {workspace?.hypotheses?.map((hypo) => {
              const hypoStatus = statusLabels[hypo.status] || { ar: hypo.status, color: "bg-slate-100" };
              const hypoType = hypothesisTypes.find((t) => t.value === hypo.hypothesis_type);
              return (
                <div
                  key={hypo.id}
                  className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
                  data-testid={`hypo-card-${hypo.id}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                        {ar ? hypoType?.ar || hypo.hypothesis_type : hypoType?.en || hypo.hypothesis_type}
                      </span>
                      <span
                        className={`rounded-md px-2 py-0.5 text-xs font-bold ${
                          hypo.importance === "CRITICAL"
                            ? "bg-red-100 text-red-800"
                            : hypo.importance === "IMPORTANT"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {hypo.importance === "CRITICAL" ? (ar ? "حرجة" : "CRITICAL") : hypo.importance}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full border px-3 py-0.5 text-xs font-semibold ${hypoStatus.color}`}
                        data-testid={`hypo-status-${hypo.id}`}
                      >
                        {ar ? hypoStatus.ar : hypo.status}
                      </span>
                    </div>
                  </div>

                  <p className="mt-3 text-base font-semibold text-slate-900">{hypo.statement}</p>
                  {hypo.rationale && <p className="mt-1 text-xs text-slate-500">{hypo.rationale}</p>}

                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3 text-xs">
                    <span className="text-slate-500">
                      {ar ? "أدلة مرتبطة:" : "Evidence count:"}{" "}
                      <strong className="text-slate-800">{hypo.evidence_count}</strong>
                    </span>

                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">{ar ? "تحديث الحالة:" : "Change Status:"}</span>
                      <button
                        onClick={() => handleUpdateHypoStatus(hypo.id, "SUPPORTED")}
                        className="rounded-md bg-emerald-50 px-2 py-1 text-emerald-800 hover:bg-emerald-100 font-medium"
                      >
                        {ar ? "مدعومة (SUPPORTED)" : "Supported"}
                      </button>
                      <button
                        onClick={() => handleUpdateHypoStatus(hypo.id, "NOT_SUPPORTED")}
                        className="rounded-md bg-red-50 px-2 py-1 text-red-800 hover:bg-red-100 font-medium"
                      >
                        {ar ? "مرفوضة (NOT_SUPPORTED)" : "Not Supported"}
                      </button>
                      <button
                        onClick={() => handleUpdateHypoStatus(hypo.id, "TESTING")}
                        className="rounded-md bg-blue-50 px-2 py-1 text-blue-800 hover:bg-blue-100 font-medium"
                      >
                        {ar ? "قيد الاختبار" : "Testing"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 2: EXPERIMENTS */}
      {subTab === "experiments" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-900">
              {ar ? "التجارب والاختبارات الميدانية" : "Validation Experiments"}
            </h3>
            <button
              onClick={() => setShowExpModal(true)}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
              data-testid="add-experiment-btn"
            >
              {ar ? "+ إضافة تجربة جديدة" : "+ Add Experiment"}
            </button>
          </div>

          <div className="grid gap-4">
            {workspace?.experiments?.map((exp) => {
              const expStatus = statusLabels[exp.status] || { ar: exp.status, color: "bg-slate-100" };
              const expType = experimentTypes.find((t) => t.value === exp.experiment_type);
              return (
                <div
                  key={exp.id}
                  className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
                  data-testid={`exp-card-${exp.id}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                      {ar ? expType?.ar || exp.experiment_type : expType?.en || exp.experiment_type}
                    </span>
                    <span className={`rounded-full border px-3 py-0.5 text-xs font-semibold ${expStatus.color}`}>
                      {ar ? expStatus.ar : exp.status}
                    </span>
                  </div>

                  <h4 className="mt-3 text-base font-bold text-slate-900">{exp.title}</h4>
                  <p className="mt-1 text-xs text-slate-600">
                    <strong>{ar ? "الهدف:" : "Objective:"}</strong> {exp.objective}
                  </p>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2 text-xs text-slate-600">
                    <div className="rounded-lg bg-slate-50 p-2.5">
                      <span className="font-semibold text-slate-700">{ar ? "المنهجية:" : "Method:"}</span>
                      <p className="mt-0.5">{exp.method}</p>
                    </div>
                    <div className="rounded-lg bg-slate-50 p-2.5">
                      <span className="font-semibold text-slate-700">{ar ? "معيار النجاح:" : "Success criteria:"}</span>
                      <p className="mt-0.5">{exp.success_criteria}</p>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs">
                    <span className="text-slate-500">
                      {ar ? "حجم العينة المستهدف:" : "Sample Size:"}{" "}
                      <strong>{exp.planned_sample_size || (ar ? "غير محدد" : "N/A")}</strong>
                    </span>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleUpdateExpStatus(exp.id, "RUNNING")}
                        className="rounded-md bg-blue-50 px-2 py-1 text-blue-800 hover:bg-blue-100"
                      >
                        {ar ? "بدء التنفيذ" : "Start"}
                      </button>
                      <button
                        onClick={() => handleUpdateExpStatus(exp.id, "COMPLETED")}
                        className="rounded-md bg-emerald-50 px-2 py-1 text-emerald-800 hover:bg-emerald-100"
                      >
                        {ar ? "اكتمال" : "Complete"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: EVIDENCE MATRIX */}
      {subTab === "evidence" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-slate-900">
                {ar ? "سجل الأدلة الميدانية الموثقة" : "Recorded Field Evidence Matrix"}
              </h3>
              <p className="text-xs text-slate-500">
                {ar
                  ? "جميع الأدلة الموثقة من مقابلات، استبيانات حقيقية، اختبارات طلب وتسعير، وروابط منافسين."
                  : "Empirical evidence from interviews, surveys, pricing tests, and competitor benchmarks."}
              </p>
            </div>
            <button
              onClick={() => setShowEvidenceModal(true)}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
              data-testid="add-evidence-btn"
            >
              {ar ? "+ توثيق دليل ميداني" : "+ Record Evidence"}
            </button>
          </div>

          <div className="grid gap-4">
            {workspace?.evidence?.map((ev) => {
              const evTypeObj = evidenceTypes.find((t) => t.value === ev.evidence_type);
              const p = ev.structured_payload || {};
              return (
                <div
                  key={ev.id}
                  className="rounded-xl border border-slate-200 bg-white p-5 shadow-xs"
                  data-testid={`evidence-item-${ev.id}`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                        {ar ? evTypeObj?.ar || ev.evidence_type : evTypeObj?.en || ev.evidence_type}
                      </span>
                      {ev.is_simulated ? (
                        <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">
                          {ar ? "⚠️ محاكاة افتراضية (لا تدعم الترقية)" : "Simulated"}
                        </span>
                      ) : (
                        <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-800">
                          {ar ? "دليل حقيقي موثق" : "Real Evidence"}
                        </span>
                      )}
                    </div>
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">
                      {ev.captured_at?.slice(0, 10)}
                    </span>
                  </div>

                  <h4 className="mt-3 text-base font-bold text-slate-900">{ev.title}</h4>
                  {ev.notes && <p className="mt-1 text-xs text-slate-600">{ev.notes}</p>}

                  {/* STRUCTURED PAYLOAD DETAILS */}
                  <div className="mt-3 rounded-xl bg-slate-50 p-3 text-xs text-slate-700 space-y-1">
                    {ev.evidence_type === "CUSTOMER_INTERVIEW" && (
                      <>
                        <p><strong>{ar ? "صفة العميل / المقابل:" : "Role:"}</strong> {p.interviewee_role || "عميل مستهدف"}</p>
                        {p.key_quote && <p className="italic">«{p.key_quote}»</p>}
                      </>
                    )}

                    {ev.evidence_type === "SURVEY_RESULT" && (
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                        <div>
                          <span className="text-slate-500">{ar ? "عدد المشاركين:" : "Responses:"}</span>{" "}
                          <strong>{p.responses_count ?? 0}</strong>
                        </div>
                        <div>
                          <span className="text-slate-500">{ar ? "الموافقون:" : "Agreed:"}</span>{" "}
                          <strong>{p.agree_count ?? 0}</strong>
                        </div>
                        <div>
                          <span className="text-slate-500">{ar ? "نسبة التأييد المحسوبة:" : "Agreement Rate:"}</span>{" "}
                          <strong>{p.derived_agreement_rate != null ? `${p.derived_agreement_rate}%` : (ar ? "غير متاح (0 مشاركين)" : "N/A")}</strong>
                        </div>
                      </div>
                    )}

                    {ev.evidence_type === "DEMAND_SIGNAL" && (
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                        <div>
                          <span className="text-slate-500">{ar ? "حجم العينة / الزيارات:" : "Impressions:"}</span>{" "}
                          <strong>{p.sample_size ?? 0}</strong>
                        </div>
                        <div>
                          <span className="text-slate-500">{ar ? "الطلبات / المهتمين:" : "Leads:"}</span>{" "}
                          <strong>{p.leads_count ?? 0}</strong>
                        </div>
                        <div>
                          <span className="text-slate-500">{ar ? "معدل التحويل المشتق:" : "Conversion Rate:"}</span>{" "}
                          <strong>{p.derived_conversion_rate != null ? `${p.derived_conversion_rate}%` : (ar ? "غير متاح" : "N/A")}</strong>
                        </div>
                      </div>
                    )}

                    {ev.evidence_type === "PRICING_TEST" && (
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                        <div>
                          <span className="text-slate-500">{ar ? "السعر المفترض:" : "Assumed Price:"}</span>{" "}
                          <strong>{p.assumed_price ?? "N/A"} ر.س</strong>
                        </div>
                        <div>
                          <span className="text-slate-500">{ar ? "السعر المختبر ميدانياً:" : "Tested Price:"}</span>{" "}
                          <strong>{p.tested_willingness_price ?? "N/A"} ر.س</strong>
                        </div>
                        <div>
                          <span className="text-slate-500">{ar ? "الفارق:" : "Difference:"}</span>{" "}
                          <strong>{p.price_difference_pct != null ? `${p.price_difference_pct}%` : "N/A"}</strong>
                        </div>
                      </div>
                    )}

                    {ev.evidence_type === "COMPETITOR_BENCHMARK" && (
                      <div>
                        <p><strong>{ar ? "المنافس المرصود:" : "Competitor:"}</strong> {p.competitor_name || "منافس مباشر"}</p>
                        {ev.source_url && (
                          <p className="mt-1">
                            <span className="text-slate-500">{ar ? "الرابط المصدري:" : "Source URL:"}</span>{" "}
                            <a
                              href={ev.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-emerald-700 underline font-medium"
                              data-testid="evidence-competitor-url"
                            >
                              {ev.source_url} ↗
                            </a>
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 4: DECISION */}
      {subTab === "decision" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-xl font-bold text-slate-900">
              {ar ? "اتخاذ قرار التحقق الميداني الرسمي" : "Record Formal Validation Decision"}
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              {ar
                ? "يقوم هذا الإجراء بتجميد لقطة غير قابلة للتعديل من الأدلة الميدانية، وتوثيق مبرر القرار وشروطه بشكل تراكمي دائم."
                : "Freezes an immutable snapshot of all recorded evidence and increments decision version."}
            </p>

            <form onSubmit={handleSubmitDecision} className="mt-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-800">
                  {ar ? "اختر القرار المعتمد:" : "Select Decision:"}
                </label>
                <div className="mt-2 grid gap-3 sm:grid-cols-4">
                  {(["GO", "GO_WITH_CONDITIONS", "PIVOT", "STOP"] as const).map((dec) => {
                    const info = decisionLabels[dec];
                    const isSelected = selectedDecision === dec;
                    return (
                      <button
                        type="button"
                        key={dec}
                        onClick={() => setSelectedDecision(dec)}
                        className={`rounded-xl border p-4 text-start transition-all ${
                          isSelected
                            ? "border-emerald-600 bg-emerald-50/70 ring-2 ring-emerald-500"
                            : "border-slate-200 bg-white hover:bg-slate-50"
                        }`}
                        data-testid={`decision-btn-${dec}`}
                      >
                        <p className={`text-sm font-bold ${isSelected ? "text-emerald-900" : "text-slate-900"}`}>
                          {ar ? info.ar : dec}
                        </p>
                        <p className="mt-1 text-xs text-slate-500 leading-snug">{info.desc}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {selectedDecision === "GO_WITH_CONDITIONS" && (
                <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 space-y-3">
                  {workspace?.evaluation?.status !== "PARTIALLY_VALIDATED" && workspace?.evaluation?.status !== "VALIDATED" && (
                    <div className="rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
                      <p className="font-bold">
                        {ar
                          ? "تنبيه حوكمة: لا يمكن اتخاذ قرار مشروط (GO_WITH_CONDITIONS) عندما تكون الحالة يحتاج لأدلة أو غير مثبت. يتطلب إثباتاً جزئياً أو كلياً."
                          : "Governance Notice: Conditional GO requires PARTIALLY_VALIDATED or VALIDATED status."}
                      </p>
                    </div>
                  )}
                  {(workspace?.evaluation?.critical_not_supported ?? 0) > 0 && (
                    <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-xs text-red-800">
                      <p className="font-bold">
                        {ar
                          ? "تنبيه حوكمة: توجد فرضيات حرجة مدحوضة بالأدلة. لا يمكن اتخاذ قرار مشروط، ويجب تغيير المسار (PIVOT) أو الإيقاف (STOP)."
                          : "Governance Notice: Refuted critical hypotheses exist. PIVOT or STOP is required."}
                      </p>
                    </div>
                  )}
                  <label className="block text-sm font-bold text-blue-900">
                    {ar ? "الشروط الملزمة للانطلاق (شرط واحد على الأقل):" : "Mandatory Conditions:"}
                  </label>
                  {decisionConditions.map((cond, idx) => (
                    <div key={idx} className="mt-2 flex gap-2">
                      <input
                        type="text"
                        value={cond}
                        onChange={(e) => {
                          const updated = [...decisionConditions];
                          updated[idx] = e.target.value;
                          setDecisionConditions(updated);
                        }}
                        placeholder={ar ? `الشرط #${idx + 1}` : `Condition #${idx + 1}`}
                        className="flex-1 rounded-lg border border-blue-300 bg-white p-2.5 text-sm"
                        data-testid={`condition-input-${idx}`}
                        required
                      />
                      {decisionConditions.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setDecisionConditions(decisionConditions.filter((_, i) => i !== idx))}
                          className="rounded-lg bg-red-100 px-3 py-1 text-xs font-bold text-red-700"
                        >
                          ✕
                        </button>
                      )}
                    </div>
                  ))}
                  <button
                    type="button"
                    onClick={() => setDecisionConditions([...decisionConditions, ""])}
                    className="mt-2 text-xs font-bold text-blue-700 hover:underline"
                  >
                    {ar ? "+ إضافة شرط آخر" : "+ Add another condition"}
                  </button>
                </div>
              )}

              <div>
                <label className="block text-sm font-semibold text-slate-800">
                  {ar ? "مبررات وأسباب القرار المستندة للأدلة:" : "Decision Rationale & Evidence Justification:"}
                </label>
                <textarea
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  rows={4}
                  required
                  placeholder={
                    ar
                      ? "اشرح بالتفصيل كيف قادت الأدلة الميدانية إلى هذا القرار..."
                      : "Provide detailed justification based on recorded evidence..."
                  }
                  className="mt-1 w-full rounded-xl border border-slate-300 p-3 text-sm focus:border-emerald-500 focus:outline-none"
                  data-testid="decision-reason-input"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  className="rounded-xl bg-emerald-600 px-6 py-3 text-sm font-bold text-white hover:bg-emerald-700 shadow-sm"
                  data-testid="submit-decision-btn"
                >
                  {ar ? "اعتماد القرار وتجميد سجل الأدلة" : "Confirm Decision & Snapshot"}
                </button>
              </div>
            </form>
          </div>

          {/* DECISION HISTORY */}
          {decisions.length > 0 && (
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h4 className="text-base font-bold text-slate-900">
                {ar ? "سجل القرارات التاريخية المعتمدة" : "Decision Audit Trail"}
              </h4>
              <div className="mt-4 space-y-3">
                {decisions.map((dec) => (
                  <div key={dec.id} className="rounded-xl border border-slate-100 bg-slate-50 p-4 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800">
                        {dec.decision} (الإصدار v{dec.decision_version})
                      </span>
                      <span className="text-slate-500">{dec.decided_at?.slice(0, 19).replace("T", " ")}</span>
                    </div>
                    <p className="mt-2 text-slate-700 text-sm">{dec.decision_reason}</p>
                    {dec.conditions && dec.conditions.length > 0 && (
                      <ul className="mt-2 list-inside list-disc text-blue-900">
                        {dec.conditions.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* MODAL: ADD HYPOTHESIS */}
      {showHypothesisModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-bold text-slate-900">
              {ar ? "إضافة فرضية ميدانية جديدة" : "Add Validation Hypothesis"}
            </h3>
            <form onSubmit={handleAddHypothesis} className="mt-4 space-y-4 text-xs sm:text-sm">
              <div>
                <label className="block font-medium text-slate-700">{ar ? "نوع الفرضية:" : "Type:"}</label>
                <select
                  value={newHypoType}
                  onChange={(e) => setNewHypoType(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                >
                  {hypothesisTypes.map((t) => (
                    <option key={t.value} value={t.value}>
                      {ar ? t.ar : t.en}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700">{ar ? "نص الفرضية:" : "Statement:"}</label>
                <textarea
                  value={newHypoStatement}
                  onChange={(e) => setNewHypoStatement(e.target.value)}
                  required
                  rows={3}
                  placeholder={ar ? "مثال: العملاء في الرياض مستعدون لدفع 35 ريال..." : "Hypothesis statement..."}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                  data-testid="hypo-statement-input"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700">{ar ? "مستوى الأهمية:" : "Importance:"}</label>
                <select
                  value={newHypoImportance}
                  onChange={(e) => setNewHypoImportance(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                >
                  <option value="CRITICAL">{ar ? "حرجة (CRITICAL - فشلها يوقف المشروع)" : "Critical"}</option>
                  <option value="IMPORTANT">{ar ? "مهمة (IMPORTANT)" : "Important"}</option>
                  <option value="NICE_TO_HAVE">{ar ? "ثانوية (NICE_TO_HAVE)" : "Nice to have"}</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700">{ar ? "المبررات والسياق:" : "Rationale:"}</label>
                <input
                  type="text"
                  value={newHypoRationale}
                  onChange={(e) => setNewHypoRationale(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowHypothesisModal(false)}
                  className="rounded-xl bg-slate-100 px-4 py-2 font-medium text-slate-700 hover:bg-slate-200"
                >
                  {ar ? "إلغاء" : "Cancel"}
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700"
                  data-testid="confirm-add-hypo-btn"
                >
                  {ar ? "حفظ الفرضية" : "Save Hypothesis"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ADD EXPERIMENT */}
      {showExpModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-slate-900">
              {ar ? "تصميم تجربة ميدانية جديدة" : "Design New Field Experiment"}
            </h3>
            <form onSubmit={handleAddExperiment} className="mt-4 space-y-4 text-xs sm:text-sm">
              <div>
                <label className="block font-medium text-slate-700">{ar ? "نوع التجربة:" : "Type:"}</label>
                <select
                  value={newExpType}
                  onChange={(e) => setNewExpType(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                >
                  {experimentTypes.map((t) => (
                    <option key={t.value} value={t.value}>
                      {ar ? t.ar : t.en}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700">{ar ? "عنوان التجربة:" : "Title:"}</label>
                <input
                  type="text"
                  value={newExpTitle}
                  onChange={(e) => setNewExpTitle(e.target.value)}
                  required
                  placeholder={ar ? "مثال: استطلاع تسعير وجبات الإفطار" : "Experiment title..."}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                  data-testid="exp-title-input"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700">{ar ? "الهدف المحدد:" : "Objective:"}</label>
                <textarea
                  value={newExpObj}
                  onChange={(e) => setNewExpObj(e.target.value)}
                  required
                  rows={2}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                  data-testid="exp-obj-input"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700">{ar ? "المنهجية وطريقة التنفيذ:" : "Method:"}</label>
                <textarea
                  value={newExpMethod}
                  onChange={(e) => setNewExpMethod(e.target.value)}
                  required
                  rows={2}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                  data-testid="exp-method-input"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700">{ar ? "معيار النجاح الرقمي:" : "Success criteria:"}</label>
                <input
                  type="text"
                  value={newExpCriteria}
                  onChange={(e) => setNewExpCriteria(e.target.value)}
                  required
                  placeholder={ar ? "مثال: موافقة 60% من عينة لا تقل عن 30 عميل" : "Success criteria..."}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                  data-testid="exp-criteria-input"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-700">{ar ? "حجم العينة المستهدف:" : "Target Sample Size:"}</label>
                <input
                  type="number"
                  value={newExpSampleSize || ""}
                  onChange={(e) => setNewExpSampleSize(e.target.value ? Number(e.target.value) : undefined)}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                  data-testid="exp-samplesize-input"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowExpModal(false)}
                  className="rounded-xl bg-slate-100 px-4 py-2 font-medium text-slate-700 hover:bg-slate-200"
                >
                  {ar ? "إلغاء" : "Cancel"}
                </button>
                <button
                  type="submit"
                  className="rounded-xl bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-700"
                  data-testid="confirm-add-exp-btn"
                >
                  {ar ? "حفظ التجربة" : "Save Experiment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: RECORD EVIDENCE */}
      {showEvidenceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-slate-900">
              {ar ? "توثيق دليل ميداني جديد" : "Record Empirical Evidence"}
            </h3>
            <form onSubmit={handleRecordEvidence} className="mt-4 space-y-4 text-xs sm:text-sm">
              <div>
                <label className="block font-medium text-slate-700">{ar ? "نوع الدليل:" : "Evidence Type:"}</label>
                <select
                  value={newEvType}
                  onChange={(e) => setNewEvType(e.target.value)}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                  data-testid="evidence-type-select"
                >
                  {evidenceTypes.map((t) => (
                    <option key={t.value} value={t.value}>
                      {ar ? t.ar : t.en}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-700">{ar ? "عنوان أو موجز الدليل:" : "Title:"}</label>
                <input
                  type="text"
                  value={newEvTitle}
                  onChange={(e) => setNewEvTitle(e.target.value)}
                  required
                  placeholder={ar ? "مثال: نتائج استبيان حي الياسمين" : "Evidence title..."}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                  data-testid="evidence-title-input"
                />
              </div>

              {/* DYNAMIC FIELDS PER EVIDENCE TYPE */}
              {newEvType === "CUSTOMER_INTERVIEW" && (
                <div className="space-y-3 rounded-xl bg-slate-50 p-3">
                  <div>
                    <label className="block font-medium text-slate-700">{ar ? "صفة / دور العميل:" : "Role:"}</label>
                    <input
                      type="text"
                      value={evInterviewRole}
                      onChange={(e) => setEvInterviewRole(e.target.value)}
                      placeholder={ar ? "مدير مشتريات / ربة منزل / موظف..." : "Role..."}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2"
                      data-testid="evidence-interview-role"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-700">{ar ? "أهم اقتباس / تصريح للعميل:" : "Key quote:"}</label>
                    <textarea
                      value={evInterviewQuote}
                      onChange={(e) => setEvInterviewQuote(e.target.value)}
                      rows={2}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2"
                      data-testid="evidence-interview-quote"
                    />
                  </div>
                </div>
              )}

              {newEvType === "SURVEY_RESULT" && (
                <div className="space-y-3 rounded-xl bg-slate-50 p-3">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block font-medium text-slate-700">{ar ? "عدد المشاركين:" : "Responses count:"}</label>
                      <input
                        type="number"
                        value={evSurveyResponses}
                        onChange={(e) => setEvSurveyResponses(e.target.value ? Number(e.target.value) : "")}
                        min="0"
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2"
                        data-testid="evidence-survey-responses"
                      />
                    </div>
                    <div>
                      <label className="block font-medium text-slate-700">{ar ? "عدد الموافقين:" : "Agree count:"}</label>
                      <input
                        type="number"
                        value={evSurveyAgreed}
                        onChange={(e) => setEvSurveyAgreed(e.target.value ? Number(e.target.value) : "")}
                        min="0"
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2"
                        data-testid="evidence-survey-agreed"
                      />
                    </div>
                  </div>
                </div>
              )}

              {newEvType === "DEMAND_SIGNAL" && (
                <div className="space-y-3 rounded-xl bg-slate-50 p-3">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block font-medium text-slate-700">{ar ? "حجم العينة / الزيارات:" : "Impressions / Sample:"}</label>
                      <input
                        type="number"
                        value={evDemandImpressions}
                        onChange={(e) => setEvDemandImpressions(e.target.value ? Number(e.target.value) : "")}
                        min="0"
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2"
                        data-testid="evidence-demand-sample"
                      />
                    </div>
                    <div>
                      <label className="block font-medium text-slate-700">{ar ? "التسجيلات / الطلبات:" : "Leads / Signups:"}</label>
                      <input
                        type="number"
                        value={evDemandLeads}
                        onChange={(e) => setEvDemandLeads(e.target.value ? Number(e.target.value) : "")}
                        min="0"
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2"
                        data-testid="evidence-demand-leads"
                      />
                    </div>
                  </div>
                </div>
              )}

              {newEvType === "PRICING_TEST" && (
                <div className="space-y-3 rounded-xl bg-slate-50 p-3">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block font-medium text-slate-700">{ar ? "السعر المفترض (ر.س):" : "Assumed Price:"}</label>
                      <input
                        type="number"
                        value={evAssumedPrice}
                        onChange={(e) => setEvAssumedPrice(e.target.value ? Number(e.target.value) : "")}
                        step="any"
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2"
                        data-testid="evidence-assumed-price"
                      />
                    </div>
                    <div>
                      <label className="block font-medium text-slate-700">{ar ? "السعر المختبر (ر.س):" : "Tested Price:"}</label>
                      <input
                        type="number"
                        value={evTestedPrice}
                        onChange={(e) => setEvTestedPrice(e.target.value ? Number(e.target.value) : "")}
                        step="any"
                        className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2"
                        data-testid="evidence-tested-price"
                      />
                    </div>
                  </div>
                </div>
              )}

              {newEvType === "COMPETITOR_BENCHMARK" && (
                <div className="space-y-3 rounded-xl bg-slate-50 p-3">
                  <div>
                    <label className="block font-medium text-slate-700">{ar ? "اسم المنافس:" : "Competitor Name:"}</label>
                    <input
                      type="text"
                      value={evCompetitorName}
                      onChange={(e) => setEvCompetitorName(e.target.value)}
                      placeholder={ar ? "مثال: بارنز كافيه" : "Competitor..."}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2"
                      data-testid="evidence-competitor-name"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-slate-700">{ar ? "رابط المصدر الميداني / الموقع (http/https) *:" : "Source URL *:"}</label>
                    <input
                      type="url"
                      value={evCompetitorUrl}
                      onChange={(e) => setEvCompetitorUrl(e.target.value)}
                      required={newEvType === "COMPETITOR_BENCHMARK"}
                      placeholder="https://example.com/pricing"
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white p-2"
                      data-testid="evidence-source-url"
                    />
                  </div>
                </div>
              )}

              {/* LINKED HYPOTHESIS SELECTION */}
              <div>
                <label className="block font-medium text-slate-700">{ar ? "ربط بفرضية محددة:" : "Link to Hypothesis:"}</label>
                <select
                  value={newEvHypoId || ""}
                  onChange={(e) => setNewEvHypoId(e.target.value ? Number(e.target.value) : undefined)}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                  data-testid="evidence-hypo-select"
                >
                  <option value="">{ar ? "-- غير محددة (دليل عام) --" : "-- None (General) --"}</option>
                  {workspace?.hypotheses?.map((h) => (
                    <option key={h.id} value={h.id}>
                      [{h.hypothesis_type}] {h.statement.slice(0, 50)}...
                    </option>
                  ))}
                </select>
              </div>

              {/* DIRECTION AND STRENGTH SELECTION */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-slate-700">
                    {ar ? "أثر الدليل على الفرضية:" : "Evidence Direction:"}
                    {newEvHypoId && <span className="text-red-500 mr-1">*</span>}
                  </label>
                  <select
                    value={newEvDirection}
                    onChange={(e) => setNewEvDirection(e.target.value as any)}
                    required={Boolean(newEvHypoId)}
                    className={`mt-1 w-full rounded-xl border p-2.5 ${
                      newEvHypoId && !newEvDirection ? "border-amber-400 bg-amber-50/50" : "border-slate-300"
                    }`}
                    data-testid="evidence-direction-select"
                  >
                    <option value="">{ar ? "-- اختر أثر الدليل على الفرضية --" : "-- Select evidence direction --"}</option>
                    <option value="SUPPORTING">{ar ? "يدعم الفرضية (SUPPORTING)" : "Supports Hypothesis (SUPPORTING)"}</option>
                    <option value="REFUTING">{ar ? "يدحض / يناقض الفرضية (REFUTING)" : "Refutes Hypothesis (REFUTING)"}</option>
                    <option value="NEUTRAL">{ar ? "محايد / غير حاسم (NEUTRAL)" : "Neutral / Inconclusive (NEUTRAL)"}</option>
                  </select>
                  {newEvHypoId && !newEvDirection && (
                    <p className="mt-1 text-xs text-amber-600">
                      {ar ? "اختر أثر الدليل على الفرضية قبل الحفظ" : "Select evidence direction before saving"}
                    </p>
                  )}
                </div>

                <div>
                  <label className="block font-medium text-slate-700">
                    {ar ? "قوة الدليل الميداني:" : "Evidence Strength:"}
                  </label>
                  <select
                    value={newEvStrength}
                    onChange={(e) => setNewEvStrength(e.target.value as any)}
                    className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                    data-testid="evidence-strength-select"
                  >
                    <option value="STRONG">{ar ? "قوي (STRONG)" : "Strong (STRONG)"}</option>
                    <option value="MODERATE">{ar ? "متوسط (MODERATE)" : "Moderate (MODERATE)"}</option>
                    <option value="WEAK">{ar ? "ضعيف (WEAK)" : "Weak (WEAK)"}</option>
                  </select>
                </div>
              </div>

              {/* SIMULATION CHECKBOX */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="simulated-checkbox"
                  checked={newEvSimulated}
                  onChange={(e) => setNewEvSimulated(e.target.checked)}
                  className="rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                  data-testid="evidence-simulated-checkbox"
                />
                <label htmlFor="simulated-checkbox" className="text-xs text-slate-700">
                  {ar
                    ? "هذا الدليل ناتج محاكاة / سيناريو افتراضي (لن يُعتد به لترقية الفرضيات)"
                    : "This is a simulated / synthetic evidence (cannot support hypotheses)"}
                </label>
              </div>

              <div>
                <label className="block font-medium text-slate-700">{ar ? "ملاحظات تفصيلية:" : "Notes:"}</label>
                <textarea
                  value={newEvNotes}
                  onChange={(e) => setNewEvNotes(e.target.value)}
                  rows={2}
                  className="mt-1 w-full rounded-xl border border-slate-300 p-2.5"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowEvidenceModal(false)}
                  className="rounded-xl bg-slate-100 px-4 py-2 font-medium text-slate-700 hover:bg-slate-200"
                >
                  {ar ? "إلغاء" : "Cancel"}
                </button>
                <button
                  type="submit"
                  disabled={Boolean(newEvHypoId && !newEvDirection)}
                  className={`rounded-xl px-4 py-2 font-medium text-white transition-all ${
                    newEvHypoId && !newEvDirection
                      ? "bg-slate-300 cursor-not-allowed text-slate-500"
                      : "bg-emerald-600 hover:bg-emerald-700"
                  }`}
                  data-testid="confirm-record-evidence-btn"
                >
                  {ar ? "حفظ الدليل" : "Save Evidence"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
