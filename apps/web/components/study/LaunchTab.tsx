"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getLaunchWorkspace,
  updateLaunchWorkspaceStatus,
  addLaunchMilestone,
  updateLaunchMilestone,
  createLaunchTask,
  updateLaunchTask,
  recordLaunchActuals,
  createLaunchReforecast,
  type LaunchWorkspaceData,
  type LaunchMilestone,
  type LaunchTask,
  type LaunchActualPeriod,
  type LaunchVarianceReport,
  type LaunchVarianceSummary,
  type LaunchReforecast,
  type LaunchWorkspaceStatus,
  type LaunchMilestoneStatus,
  type LaunchTaskStatus,
} from "@/lib/api";

const milestoneCategories = [
  { value: "REGULATORY", ar: "التراخيص والمتطلبات النظامية (بلدي، تجارة)", en: "Regulatory & Licenses" },
  { value: "LOCATION", ar: "الموقع التجاري والتشطيبات والمعدات", en: "Location & Fitout" },
  { value: "EQUIPMENT", ar: "تجهيز وتوريد الآلات والمعدات", en: "Equipment & Assets" },
  { value: "TEAM", ar: "التوظيف والتعاقد ونسب التوطين (قوى)", en: "Team & Qiwa" },
  { value: "MARKETING", ar: "الحملة التسويقية والتسجيل المسبق", en: "Pre-Launch Marketing" },
  { value: "OPERATIONS", ar: "الافتتاح والربط مع الفوترة الإلكترونية (زاتكا)", en: "Operations & ZATCA" },
];

const workspaceStatusMap: Record<string, { ar: string; badge: string }> = {
  PLANNED: { ar: "مخطط للإطلاق", badge: "bg-slate-100 text-slate-800 border-slate-300" },
  IN_PROGRESS: { ar: "قيد التجهيز الفعلي", badge: "bg-blue-100 text-blue-800 border-blue-300" },
  BLOCKED: { ar: "معطل / متعثر", badge: "bg-red-100 text-red-800 border-red-300" },
  LAUNCHED: { ar: "تم الإطلاق الرسمي", badge: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  PAUSED: { ar: "موقوف مؤقتاً", badge: "bg-amber-100 text-amber-800 border-amber-300" },
  CANCELLED: { ar: "ملغى", badge: "bg-gray-100 text-gray-700 border-gray-300" },
};

const milestoneStatusMap: Record<string, { ar: string; badge: string }> = {
  PENDING: { ar: "قيد الانتظار", badge: "bg-slate-100 text-slate-700 border-slate-300" },
  IN_PROGRESS: { ar: "جارٍ التنفيذ", badge: "bg-blue-100 text-blue-700 border-blue-300" },
  COMPLETED: { ar: "مكتمل بنجاح", badge: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  BLOCKED: { ar: "معطل / متعثر", badge: "bg-red-100 text-red-800 border-red-300" },
  DELAYED: { ar: "مؤجل / متأخر", badge: "bg-amber-100 text-amber-800 border-amber-300" },
};

const taskStatusMap: Record<string, { ar: string; badge: string }> = {
  PENDING: { ar: "قيد الانتظار", badge: "bg-slate-100 text-slate-700 border-slate-300" },
  IN_PROGRESS: { ar: "جارٍ التنفيذ", badge: "bg-blue-100 text-blue-700 border-blue-300" },
  COMPLETED: { ar: "مكتملة", badge: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  BLOCKED: { ar: "معطلة", badge: "bg-red-100 text-red-800 border-red-300" },
  CANCELLED: { ar: "ملغاة", badge: "bg-gray-100 text-gray-700 border-gray-300" },
};

const alertLevelMap: Record<string, { ar: string; badge: string; desc: string }> = {
  NORMAL: {
    ar: "أداء اعتيادي ومستقر",
    badge: "bg-emerald-100 text-emerald-800 border-emerald-300",
    desc: "الانحراف أقل من 10% مقارنة بخط الأساس المعتمد.",
  },
  WATCH: {
    ar: "تنبيه مراقبة وتحفظ",
    badge: "bg-amber-100 text-amber-800 border-amber-300",
    desc: "انحراف بين 10% و 25% يتطلب مراجعة النفقات وتدفق الإيراد.",
  },
  MATERIAL_VARIANCE: {
    ar: "انحراف مالي جوهري",
    badge: "bg-red-100 text-red-800 border-red-300 animate-pulse",
    desc: "انحراف يتجاوز 25% يستدعي تحديث خطة السيولة وإجراء إعادة تنبؤ فوري.",
  },
  NOT_AVAILABLE: {
    ar: "غير متوفر للحساب",
    badge: "bg-slate-100 text-slate-700 border-slate-300",
    desc: "لا يمكن حساب الانحراف لعدم توفر بيانات خط الأساس التقديري أو الأداء الفعلي بالكامل.",
  },
};

export default function LaunchTab({
  studyId,
  token,
  locale = "ar",
}: {
  studyId: number;
  token: string;
  locale?: "ar" | "en";
}) {
  const ar = locale === "ar";
  const [workspaceData, setWorkspaceData] = useState<LaunchWorkspaceData | null>(null);
  const [subTab, setSubTab] = useState<"milestones" | "tasks" | "actuals" | "variances" | "reforecast">("milestones");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Status Modal/Change State
  const [changingStatus, setChangingStatus] = useState(false);
  const [targetStatus, setTargetStatus] = useState("IN_PROGRESS");
  const [actualLaunchDate, setActualLaunchDate] = useState("");

  // Milestone Form State (No synthetic budgets!)
  const [newMilestoneCategory, setNewMilestoneCategory] = useState("REGULATORY");
  const [newMilestoneTitle, setNewMilestoneTitle] = useState("");
  const [newMilestoneBudget, setNewMilestoneBudget] = useState("");
  const [newMilestoneDesc, setNewMilestoneDesc] = useState("");
  const [newMilestoneOwner, setNewMilestoneOwner] = useState("");

  // Task Form State
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskMilestoneId, setNewTaskMilestoneId] = useState<string>("");
  const [newTaskOwner, setNewTaskOwner] = useState("");
  const [newTaskDueDate, setNewTaskDueDate] = useState("");
  const [newTaskCritical, setNewTaskCritical] = useState(false);

  // Actuals Form State (No fake defaults: empty strings!)
  const [actualPeriodNum, setActualPeriodNum] = useState("1");
  const [actualPeriodLabel, setActualPeriodLabel] = useState("M01");
  const [actualRevenue, setActualRevenue] = useState("");
  const [actualVolume, setActualVolume] = useState("");
  const [actualCapex, setActualCapex] = useState("");
  const [actualSalaries, setActualSalaries] = useState("");
  const [actualRent, setActualRent] = useState("");
  const [actualInventory, setActualInventory] = useState("");
  const [actualMarketing, setActualMarketing] = useState("");
  const [actualUtilities, setActualUtilities] = useState("");
  const [actualClosingCash, setActualClosingCash] = useState("");
  const [actualSourceType, setActualSourceType] = useState("USER_ENTERED");
  const [actualSourceRef, setActualSourceRef] = useState("");
  const [actualNotes, setActualNotes] = useState("");

  // Reforecast Form State (No fake defaults!)
  const [reforecastTitle, setReforecastTitle] = useState("");
  const [reforecastReason, setReforecastReason] = useState("");
  const [reforecastRevAdj, setReforecastRevAdj] = useState("0");
  const [reforecastCostAdj, setReforecastCostAdj] = useState("0");
  const [reforecastCashBalance, setReforecastCashBalance] = useState("");

  const [savingAction, setSavingAction] = useState(false);

  const fetchWorkspace = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getLaunchWorkspace(token, studyId);
      setWorkspaceData(data);
      if (data.actual_periods && data.actual_periods.length > 0) {
        const nextPeriod = data.actual_periods.length + 1;
        setActualPeriodNum(String(nextPeriod));
        setActualPeriodLabel(`M${String(nextPeriod).padStart(2, "0")}`);
      }
    } catch (err: any) {
      setError(err?.message || "فشل تحميل مساحة الإطلاق والأداء الفعلي.");
    } finally {
      setLoading(false);
    }
  }, [token, studyId]);

  useEffect(() => {
    fetchWorkspace();
  }, [fetchWorkspace]);

  const handleUpdateStatus = async (status: LaunchWorkspaceStatus, launchDate?: string) => {
    if (!workspaceData) return;
    try {
      setSavingAction(true);
      setError(null);
      await updateLaunchWorkspaceStatus(token, workspaceData.id, {
        status,
        actual_launch_date: status === "LAUNCHED" ? (launchDate || new Date().toISOString().slice(0, 10)) : undefined,
      });
      setActionSuccess(ar ? `تم تغيير حالة مساحة الإطلاق إلى ${status}` : `Workspace transitioned to ${status}`);
      setChangingStatus(false);
      await fetchWorkspace();
    } catch (err: any) {
      setError(err?.message || "تعذر تحديث حالة مساحة الإطلاق.");
    } finally {
      setSavingAction(false);
    }
  };

  const handleAddMilestone = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceData) return;
    try {
      setSavingAction(true);
      setError(null);
      await addLaunchMilestone(token, workspaceData.id, {
        category: newMilestoneCategory,
        title: newMilestoneTitle,
        description: newMilestoneDesc || undefined,
        budget_allocated: newMilestoneBudget ? parseFloat(newMilestoneBudget) : null,
        owner_name: newMilestoneOwner || undefined,
      });
      setNewMilestoneTitle("");
      setNewMilestoneDesc("");
      setNewMilestoneBudget("");
      setNewMilestoneOwner("");
      setActionSuccess(ar ? "تمت إضافة المعلم بنجاح" : "Milestone added successfully");
      await fetchWorkspace();
    } catch (err: any) {
      setError(err?.message || "تعذر حفظ المعلم.");
    } finally {
      setSavingAction(false);
    }
  };

  const handleUpdateMilestone = async (milestoneId: number, status: LaunchMilestoneStatus, cost?: number) => {
    try {
      setSavingAction(true);
      setError(null);
      await updateLaunchMilestone(token, milestoneId, {
        status,
        actual_cost: cost !== undefined ? cost : undefined,
        completed_date: status === "COMPLETED" ? new Date().toISOString().slice(0, 10) : undefined,
      });
      setActionSuccess(ar ? "تم تحديث حالة المعلم بنجاح" : "Milestone updated");
      await fetchWorkspace();
    } catch (err: any) {
      setError(err?.message || "فشل تحديث المعلم.");
    } finally {
      setSavingAction(false);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceData) return;
    try {
      setSavingAction(true);
      setError(null);
      await createLaunchTask(token, workspaceData.id, {
        title: newTaskTitle,
        milestone_id: newTaskMilestoneId ? parseInt(newTaskMilestoneId, 10) : null,
        owner_name: newTaskOwner || undefined,
        due_date: newTaskDueDate || undefined,
        is_critical: newTaskCritical,
      });
      setNewTaskTitle("");
      setNewTaskOwner("");
      setNewTaskDueDate("");
      setNewTaskCritical(false);
      setActionSuccess(ar ? "تمت إضافة المهمة التنفيذية بنجاح" : "Task added successfully");
      await fetchWorkspace();
    } catch (err: any) {
      setError(err?.message || "تعذر إنشاء المهمة.");
    } finally {
      setSavingAction(false);
    }
  };

  const handleUpdateTask = async (taskId: number, status: LaunchTaskStatus) => {
    try {
      setSavingAction(true);
      setError(null);
      await updateLaunchTask(token, taskId, {
        status,
        completed_date: status === "COMPLETED" ? new Date().toISOString().slice(0, 10) : undefined,
      });
      setActionSuccess(ar ? "تم تحديث حالة المهمة" : "Task status updated");
      await fetchWorkspace();
    } catch (err: any) {
      setError(err?.message || "تعذر تحديث المهمة.");
    } finally {
      setSavingAction(false);
    }
  };

  const handleRecordActuals = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceData) return;
    try {
      setSavingAction(true);
      setError(null);

      const opexSalaries = actualSalaries !== "" ? parseFloat(actualSalaries) : null;
      const opexRent = actualRent !== "" ? parseFloat(actualRent) : null;
      const opexInventory = actualInventory !== "" ? parseFloat(actualInventory) : null;
      const opexMarketing = actualMarketing !== "" ? parseFloat(actualMarketing) : null;
      const opexUtilities = actualUtilities !== "" ? parseFloat(actualUtilities) : null;

      await recordLaunchActuals(token, workspaceData.id, {
        period_order: parseInt(actualPeriodNum, 10) || 1,
        period_label: actualPeriodLabel,
        actual_revenue: actualRevenue !== "" ? parseFloat(actualRevenue) : null,
        transactions_count: actualVolume !== "" ? parseInt(actualVolume, 10) : null,
        actual_capex: actualCapex !== "" ? parseFloat(actualCapex) : null,
        actual_opex_salaries: opexSalaries,
        actual_opex_rent: opexRent,
        actual_opex_cogs: opexInventory,
        actual_opex_marketing: opexMarketing,
        actual_opex_utilities: opexUtilities,
        closing_cash_balance: actualClosingCash !== "" ? parseFloat(actualClosingCash) : null,
        source_type: actualSourceType,
        source_reference: actualSourceRef || undefined,
        notes: actualNotes || undefined,
      });

      setActionSuccess(ar ? "تم تسجيل بيانات الفترة الفعلية وحساب الفروقات آلياً دون افتراضات" : "Actual period recorded");
      await fetchWorkspace();
      setSubTab("variances");
    } catch (err: any) {
      setError(err?.message || "تعذر تسجيل الأداء الفعلي.");
    } finally {
      setSavingAction(false);
    }
  };

  const handleCreateReforecast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceData) return;
    try {
      setSavingAction(true);
      setError(null);
      await createLaunchReforecast(token, workspaceData.id, {
        reforecast_title: reforecastTitle || (ar ? "سيناريو إعادة تنبؤ محدث" : "Dynamic Reforecast"),
        adjustment_rationale: reforecastReason || (ar ? "تعديل سيناريو التنبؤ بناء على المستجدات الفعلية" : "Operational variance update"),
        growth_rate_adjustment_pct: parseFloat(reforecastRevAdj) || 0,
        opex_adjustment_pct: parseFloat(reforecastCostAdj) || 0,
        explicit_cash_balance: reforecastCashBalance !== "" ? parseFloat(reforecastCashBalance) : null,
      });
      setActionSuccess(ar ? "تم توليد سيناريو إعادة التنبؤ الموسوم كافتراض مستخدم وحساب المؤشرات" : "Reforecast generated");
      await fetchWorkspace();
    } catch (err: any) {
      setError(err?.message || "تعذر إنشاء سيناريو إعادة التنبؤ.");
    } finally {
      setSavingAction(false);
    }
  };

  if (loading && !workspaceData) {
    return (
      <div className="p-8 text-center" dir={ar ? "rtl" : "ltr"}>
        <div className="inline-block w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm text-slate-600 font-medium">
          {ar ? "جارٍ تحميل نظام الإطلاق وتتبع الأداء الفعلي..." : "Loading Launch & Actuals OS..."}
        </p>
      </div>
    );
  }

  const gate = workspaceData?.decision_gate;
  const milestones = workspaceData?.milestones || [];
  const tasks = workspaceData?.tasks || [];
  const actualPeriods = workspaceData?.actual_periods || [];
  const varianceSummary = workspaceData?.variances_summary || workspaceData?.variance_summary;
  const activeBaseline = workspaceData?.active_baseline;
  const latestReforecast = workspaceData?.latest_reforecast;
  const currentStatus = workspaceData?.status || "PLANNED";
  const statusMeta = workspaceStatusMap[currentStatus] || workspaceStatusMap.PLANNED;

  const totalAllocatedBudget = milestones.reduce((s, m) => s + (m.budget_allocated || 0), 0);
  const totalActualMilestoneCost = milestones.reduce((s, m) => s + (m.actual_cost || 0), 0);
  const completedMilestonesCount = milestones.filter((m) => m.status === "COMPLETED").length;
  const completedTasksCount = tasks.filter((t) => t.status === "COMPLETED").length;

  return (
    <div className="space-y-6" dir={ar ? "rtl" : "ltr"} data-testid="launch-os-workspace">
      {/* HEADER & STATUS BAR */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-indigo-100 text-indigo-800 border border-indigo-200">
                {ar ? "الموجة 5: نظام الإطلاق والأداء الفعلي (Launch OS)" : "Wave 5: Launch & Actuals OS"}
              </span>
              <span className={`px-2.5 py-0.5 text-xs font-bold rounded-full border ${statusMeta.badge}`}>
                {statusMeta.ar}
              </span>
              {workspaceData?.actual_launch_date && (
                <span className="text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
                  {ar ? `تاريخ الإطلاق: ${workspaceData.actual_launch_date}` : `Launched: ${workspaceData.actual_launch_date}`}
                </span>
              )}
            </div>
            <h2 className="text-xl font-bold text-slate-900">
              {ar ? "تنفيذ الإطلاق ومقارنة الأداء الفعلي والتنبؤ التكيفي" : "Launch Execution, Actuals & Reforecasting"}
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              {ar
                ? "إدارة مهام ومعالم الإطلاق، مقارنة الفعليات مع خط الأساس المجمد بدون تزييف، ومراقبة السيولة النقدية دون دمج الاستثمار كرصيد كاش."
                : "Manage launch milestones & tasks, track actuals against frozen baseline, and calculate real cash runway."}
            </p>
          </div>

          {/* DECISION GATE BADGE & STATUS ACTIONS */}
          <div className="flex flex-col sm:flex-row items-end sm:items-center gap-3">
            {gate && (
              <div
                className={`p-3 rounded-lg border text-sm font-medium ${
                  gate.is_allowed
                    ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                    : "bg-red-50 border-red-200 text-red-900"
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className="text-base">{gate.is_allowed ? "🔓" : "🔒"}</span>
                  <span className="font-bold">
                    {gate.is_allowed
                      ? ar
                        ? `بوابة الإطلاق مفتوحة (${gate.decision})`
                        : `Launch Gate Unlocked (${gate.decision})`
                      : ar
                      ? "بوابة الإطلاق مقفلة بقرار التحقق"
                      : "Launch Gate Locked by Validation"}
                  </span>
                </div>
                <p className="text-xs mt-1 text-slate-600 max-w-sm">{gate.reason}</p>
              </div>
            )}

            {/* STATUS TRANSITION BUTTON */}
            {gate?.is_allowed && (
              <button
                onClick={() => setChangingStatus(!changingStatus)}
                className="px-3 py-2 text-xs font-bold bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition"
              >
                ⚙️ {ar ? "تغيير حالة الإطلاق" : "Change Status"}
              </button>
            )}
          </div>
        </div>

        {/* STATUS TRANSITION MODAL / PANEL */}
        {changingStatus && (
          <div className="mt-4 p-4 bg-slate-50 border border-slate-300 rounded-lg">
            <h4 className="font-bold text-xs text-slate-800 mb-2">
              {ar ? "تحديث حالة دورة حياة مساحة الإطلاق:" : "Update Launch Lifecycle Status:"}
            </h4>
            <div className="flex flex-wrap items-center gap-2">
              {(["PLANNED", "IN_PROGRESS", "BLOCKED", "LAUNCHED", "PAUSED", "CANCELLED"] as LaunchWorkspaceStatus[]).map((st) => (
                <button
                  key={st}
                  onClick={() => handleUpdateStatus(st, actualLaunchDate)}
                  disabled={savingAction || currentStatus === st}
                  className={`px-3 py-1 text-xs font-bold rounded-lg border transition ${
                    currentStatus === st
                      ? "bg-slate-300 text-slate-600 border-slate-400 cursor-not-allowed"
                      : st === "LAUNCHED"
                      ? "bg-emerald-600 text-white border-emerald-700 hover:bg-emerald-700"
                      : "bg-white text-slate-800 border-slate-300 hover:bg-slate-100"
                  }`}
                >
                  {workspaceStatusMap[st]?.ar || st}
                </button>
              ))}
              <button
                onClick={() => setChangingStatus(false)}
                className="px-2.5 py-1 text-xs text-slate-500 hover:text-slate-800"
              >
                {ar ? "إلغاء" : "Cancel"}
              </button>
            </div>
          </div>
        )}

        {/* FEEDBACK ALERTS */}
        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-xs underline font-semibold">
              {ar ? "إغلاق" : "Dismiss"}
            </button>
          </div>
        )}

        {actionSuccess && (
          <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm rounded-lg flex items-center justify-between">
            <span>{actionSuccess}</span>
            <button onClick={() => setActionSuccess(null)} className="text-xs underline font-semibold">
              {ar ? "إغلاق" : "Dismiss"}
            </button>
          </div>
        )}

        {/* GATE RESTRICTION BANNER */}
        {gate && !gate.is_allowed && (
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-sm">
            <h4 className="font-bold text-base mb-1">
              ⚠️ {ar ? "تنبيه الحوكمة المالية والتشغيلية" : "Operational Governance Alert"}
            </h4>
            <p>
              {ar
                ? "وفقاً لمحددات الحوكمة، لا يمكن بدء عمليات الإطلاق الفعلي أو تسجيل المصاريف التشغيلية للمشاريع التي صدر لها قرار إيقاف (STOP) أو تتطلب تعديل مسار (PIVOT) أو لم يصدر لها قرار بعد. يرجى مراجعة تبويب التحقق الميداني لتسجيل الأدلة وتوثيق قرار GO أو GO_WITH_CONDITIONS."
                : "Projects with a STOP, PIVOT, or missing validation decision are blocked from launching. Please review Market Validation tab."}
            </p>
          </div>
        )}

        {/* NAVIGATION TABS */}
        <div className="flex border-b border-slate-200 mt-6 gap-2">
          <button
            onClick={() => setSubTab("milestones")}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 transition ${
              subTab === "milestones"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {ar ? `معالم الإطلاق (${milestones.length})` : `Milestones (${milestones.length})`}
          </button>
          <button
            onClick={() => setSubTab("tasks")}
            data-testid="launch-tasks-tab"
            className={`pb-3 px-4 text-sm font-semibold border-b-2 transition ${
              subTab === "tasks"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {ar ? `المهام التنفيذية (${tasks.length})` : `Tasks (${tasks.length})`}
          </button>
          <button
            onClick={() => setSubTab("actuals")}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 transition ${
              subTab === "actuals"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {ar ? `تسجيل الأداء الفعلي (${actualPeriods.length})` : `Record Actuals (${actualPeriods.length})`}
          </button>
          <button
            onClick={() => setSubTab("variances")}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 transition ${
              subTab === "variances"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {ar ? "مقارنة التوقعات مع الفعلي (Variance)" : "Forecast vs Actual Matrix"}
          </button>
          <button
            onClick={() => setSubTab("reforecast")}
            className={`pb-3 px-4 text-sm font-semibold border-b-2 transition ${
              subTab === "reforecast"
                ? "border-emerald-600 text-emerald-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {ar ? "إعادة التنبؤ ومدرج السيولة" : "Reforecast & Runway"}
          </button>
        </div>
      </div>

      {/* SUBTAB 1: MILESTONES */}
      {subTab === "milestones" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 font-medium">{ar ? "إجمالي المعالم" : "Total Milestones"}</span>
              <p className="text-2xl font-bold text-slate-800 mt-1">{milestones.length}</p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 font-medium">{ar ? "المعالم المكتملة" : "Completed"}</span>
              <p className="text-2xl font-bold text-emerald-600 mt-1">
                {completedMilestonesCount} / {milestones.length}
              </p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 font-medium">{ar ? "الميزانية المخصصة فعلياً" : "Allocated Budget"}</span>
              <p className="text-2xl font-bold text-indigo-700 mt-1">
                {totalAllocatedBudget > 0 ? totalAllocatedBudget.toLocaleString() : "—"}{" "}
                <span className="text-xs font-normal text-slate-500">ر.س</span>
              </p>
            </div>
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <span className="text-xs text-slate-500 font-medium">{ar ? "المصروف الفعلي" : "Actual Cost"}</span>
              <p className="text-2xl font-bold text-slate-900 mt-1">
                {totalActualMilestoneCost > 0 ? totalActualMilestoneCost.toLocaleString() : "—"}{" "}
                <span className="text-xs font-normal text-slate-500">ر.س</span>
              </p>
            </div>
          </div>

          {/* MILESTONES LIST */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">
                {ar ? "خطة معالم التأسيس والتشغيل (بدون ميزانيات مصطنعة)" : "Milestones (No Synthetic Budgets)"}
              </h3>
              <span className="text-xs text-slate-500">
                {ar ? "الميزانيات فارغة حتى يحددها المؤسس" : "Budgets remain null until allocated"}
              </span>
            </div>

            <div className="divide-y divide-slate-100">
              {milestones.map((m) => {
                const catObj = milestoneCategories.find((c) => c.value === m.category);
                const stMeta = milestoneStatusMap[m.status] || milestoneStatusMap.PENDING;
                return (
                  <div key={m.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full border ${stMeta.badge}`}>
                          {stMeta.ar}
                        </span>
                        <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                          {catObj ? catObj.ar : m.category}
                        </span>
                        {m.is_suggested && (
                          <span className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                            {ar ? "عنصر مقترح - تأكيد الانطباق" : "Suggested"}
                          </span>
                        )}
                      </div>
                      <h4 className="font-bold text-slate-800 text-sm">{m.title}</h4>
                      {m.description && <p className="text-xs text-slate-600 max-w-xl">{m.description}</p>}
                      {m.owner_name && (
                        <p className="text-[11px] text-slate-500">
                          {ar ? "المسؤول: " : "Owner: "} <span className="font-semibold">{m.owner_name}</span>
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <div className="text-xs text-slate-500">{ar ? "المخصص / الفعلي" : "Budget / Actual"}</div>
                        <div className="text-sm font-semibold text-slate-800">
                          {m.budget_allocated !== null ? `${m.budget_allocated.toLocaleString()} ر.س` : (ar ? "غير محدد" : "None")} /{" "}
                          <span className={m.actual_cost && m.budget_allocated && m.actual_cost > m.budget_allocated ? "text-red-600" : "text-emerald-600"}>
                            {m.actual_cost !== null ? `${m.actual_cost.toLocaleString()} ر.س` : (ar ? "لم يسجل" : "Pending")}
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        {m.status !== "COMPLETED" && (
                          <button
                            disabled={savingAction}
                            onClick={() => handleUpdateMilestone(m.id, "COMPLETED", m.actual_cost ?? (m.budget_allocated ?? 0))}
                            className="px-2.5 py-1 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded hover:bg-emerald-100 transition"
                          >
                            ✓ {ar ? "إكمال" : "Complete"}
                          </button>
                        )}
                        {m.status !== "IN_PROGRESS" && m.status !== "COMPLETED" && (
                          <button
                            disabled={savingAction}
                            onClick={() => handleUpdateMilestone(m.id, "IN_PROGRESS")}
                            className="px-2.5 py-1 text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition"
                          >
                            ▶ {ar ? "بدء" : "Start"}
                          </button>
                        )}
                        {m.status !== "BLOCKED" && (
                          <button
                            disabled={savingAction}
                            onClick={() => handleUpdateMilestone(m.id, "BLOCKED")}
                            className="px-2.5 py-1 text-xs font-semibold bg-red-50 text-red-700 border border-red-200 rounded hover:bg-red-100 transition"
                          >
                            ✕ {ar ? "تعثر" : "Block"}
                          </button>
                        )}
                        {m.status !== "DELAYED" && m.status !== "COMPLETED" && (
                          <button
                            disabled={savingAction}
                            onClick={() => handleUpdateMilestone(m.id, "DELAYED")}
                            className="px-2.5 py-1 text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 rounded hover:bg-amber-100 transition"
                          >
                            ⏳ {ar ? "تأجيل" : "Delay"}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* ADD MILESTONE FORM */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
            <h3 className="font-bold text-slate-900 text-sm mb-4">
              {ar ? "إضافة معلم تأسيسي / تشغيلي جديد" : "Add Launch Milestone"}
            </h3>
            <form onSubmit={handleAddMilestone} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "التصنيف التشغيلي" : "Category"}
                  </label>
                  <select
                    value={newMilestoneCategory}
                    onChange={(e) => setNewMilestoneCategory(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                  >
                    {milestoneCategories.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.ar}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "عنوان المعلم" : "Title"}
                  </label>
                  <input
                    type="text"
                    required
                    value={newMilestoneTitle}
                    onChange={(e) => setNewMilestoneTitle(e.target.value)}
                    placeholder={ar ? "مثال: رخصة الدفاع المدني" : "e.g. Civil Defense Permit"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "الميزانية المخصصة (اختياري)" : "Budget (Optional)"}
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="100"
                    value={newMilestoneBudget}
                    onChange={(e) => setNewMilestoneBudget(e.target.value)}
                    placeholder={ar ? "اترك فارغاً إن لم تحدد" : "Leave blank if unknown"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "المسؤول (اختياري)" : "Owner"}
                  </label>
                  <input
                    type="text"
                    value={newMilestoneOwner}
                    onChange={(e) => setNewMilestoneOwner(e.target.value)}
                    placeholder={ar ? "اسم المسؤول" : "Owner Name"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  {ar ? "التفاصيل والمتطلبات" : "Description"}
                </label>
                <textarea
                  rows={2}
                  value={newMilestoneDesc}
                  onChange={(e) => setNewMilestoneDesc(e.target.value)}
                  placeholder={ar ? "متطلبات التنفيذ..." : "Details..."}
                  className="w-full text-sm border border-slate-300 rounded-lg p-2"
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={savingAction || !newMilestoneTitle}
                  className="px-4 py-2 text-sm font-bold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition"
                >
                  {savingAction ? (ar ? "جارٍ الإضافة..." : "Adding...") : ar ? "+ حفظ المعلم" : "+ Add Milestone"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* SUBTAB 2: TASKS */}
      {subTab === "tasks" && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
            <h3 className="font-bold text-slate-900 text-sm mb-4">
              {ar ? "إضافة مهمة تنفيذية لمسار الإطلاق" : "Add Launch Task"}
            </h3>
            <form onSubmit={handleCreateTask} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "عنوان المهمة" : "Task Title"}
                  </label>
                  <input
                    type="text"
                    required
                    value={newTaskTitle}
                    onChange={(e) => setNewTaskTitle(e.target.value)}
                    data-testid="launch-task-title"
                    placeholder={ar ? "مثال: سداد رسوم الفاتورة الإلكترونية عبر سداد" : "e.g. Pay licensing fee"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "ربط بمعلم (اختياري)" : "Link to Milestone"}
                  </label>
                  <select
                    value={newTaskMilestoneId}
                    onChange={(e) => setNewTaskMilestoneId(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                  >
                    <option value="">{ar ? "-- غير مرتبط بمعلم --" : "-- No milestone --"}</option>
                    {milestones.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.title}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "المسؤول عن التنفيذ" : "Assignee / Owner"}
                  </label>
                  <input
                    type="text"
                    value={newTaskOwner}
                    onChange={(e) => setNewTaskOwner(e.target.value)}
                    placeholder={ar ? "اسم المنفذ" : "Assignee"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>

              <div className="flex items-center gap-6">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "تاريخ الاستحقاق" : "Due Date"}
                  </label>
                  <input
                    type="date"
                    value={newTaskDueDate}
                    onChange={(e) => setNewTaskDueDate(e.target.value)}
                    className="text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div className="flex items-center gap-2 pt-5">
                  <input
                    type="checkbox"
                    id="is_crit"
                    checked={newTaskCritical}
                    onChange={(e) => setNewTaskCritical(e.target.checked)}
                    className="rounded border-slate-300 text-red-600 focus:ring-red-500"
                  />
                  <label htmlFor="is_crit" className="text-xs font-bold text-red-700">
                    {ar ? "مهمة حرجة للإطلاق (Critical)" : "Critical Launch Task"}
                  </label>
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={savingAction || !newTaskTitle}
                  data-testid="launch-add-task"
                  className="px-4 py-2 text-sm font-bold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition"
                >
                  {savingAction ? (ar ? "جارٍ الحفظ..." : "Saving...") : ar ? "+ إضافة المهمة" : "+ Add Task"}
                </button>
              </div>
            </form>
          </div>

          {/* TASKS LIST */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">
                {ar ? `قائمة المهام التنفيذية (${completedTasksCount} / ${tasks.length} مكتملة)` : `Execution Tasks (${completedTasksCount}/${tasks.length})`}
              </h3>
            </div>

            {tasks.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">
                {ar ? "لا توجد مهام مضافة بعد. استخدم النموذج أعلاه لجدولة المهام." : "No tasks added yet."}
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {tasks.map((t) => (
                  <div key={t.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 text-xs font-semibold rounded-full border ${
                            taskStatusMap[t.status]?.badge || "bg-slate-100 text-slate-700 border-slate-300"
                          }`}
                        >
                          {taskStatusMap[t.status]?.ar || t.status}
                        </span>
                        {t.is_critical && (
                          <span className="text-[10px] font-bold bg-red-100 text-red-800 border border-red-200 px-2 py-0.5 rounded-full">
                            {ar ? "حرجة" : "Critical"}
                          </span>
                        )}
                        {t.owner_name && (
                          <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                            {t.owner_name}
                          </span>
                        )}
                      </div>
                      <h4 className="font-bold text-slate-800 text-sm">{t.title}</h4>
                      {t.due_date && (
                        <p className="text-xs text-slate-500">
                          {ar ? `الاستحقاق: ${t.due_date}` : `Due: ${t.due_date}`}
                        </p>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      {t.status !== "COMPLETED" && (
                        <button
                          disabled={savingAction}
                          onClick={() => handleUpdateTask(t.id, "COMPLETED")}
                          className="px-2.5 py-1 text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 rounded hover:bg-emerald-100 transition"
                        >
                          ✓ {ar ? "إنجاز" : "Complete"}
                        </button>
                      )}
                      {t.status !== "IN_PROGRESS" && t.status !== "COMPLETED" && (
                        <button
                          disabled={savingAction}
                          onClick={() => handleUpdateTask(t.id, "IN_PROGRESS")}
                          className="px-2.5 py-1 text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition"
                        >
                          ▶ {ar ? "بدء" : "Start"}
                        </button>
                      )}
                      {t.status !== "BLOCKED" && (
                        <button
                          disabled={savingAction}
                          onClick={() => handleUpdateTask(t.id, "BLOCKED")}
                          className="px-2.5 py-1 text-xs font-semibold bg-red-50 text-red-700 border border-red-200 rounded hover:bg-red-100 transition"
                        >
                          ✕ {ar ? "تعثر" : "Block"}
                        </button>
                      )}
                      {t.status !== "CANCELLED" && t.status !== "COMPLETED" && (
                        <button
                          disabled={savingAction}
                          onClick={() => handleUpdateTask(t.id, "CANCELLED")}
                          className="px-2.5 py-1 text-xs font-semibold bg-gray-50 text-gray-700 border border-gray-200 rounded hover:bg-gray-100 transition"
                        >
                          ✕ {ar ? "إلغاء" : "Cancel"}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUBTAB 3: RECORD ACTUALS */}
      {subTab === "actuals" && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-slate-900 text-base">
                  {ar ? "تسجيل بيانات الشهر الفعلي (بدون قيم افتراضية زائفة)" : "Record Monthly Actuals (Unknown != Zero)"}
                </h3>
                <p className="text-xs text-slate-600 mt-0.5">
                  {ar
                    ? "القيم المتروكة فارغة تبقى غير معروفة ولا تُعامل كصفر. الصفر يعني إثبات حقيقي بعدم وجود مبيعات."
                    : "Blank inputs remain unknown (None), not 0. Zero means verified zero."}
                </p>
              </div>
              <span className="text-xs px-2.5 py-1 bg-indigo-50 text-indigo-700 font-semibold rounded-full border border-indigo-100">
                {ar ? "توثيق مصدر البيانات" : "Provenance Aware"}
              </span>
            </div>

            <form onSubmit={handleRecordActuals} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "رقم الفترة (الشهر)" : "Period Number"}
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={actualPeriodNum}
                    onChange={(e) => {
                      setActualPeriodNum(e.target.value);
                      setActualPeriodLabel(`M${String(e.target.value).padStart(2, "0")}`);
                    }}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "تسمية الفترة" : "Period Label"}
                  </label>
                  <input
                    type="text"
                    required
                    value={actualPeriodLabel}
                    onChange={(e) => setActualPeriodLabel(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-slate-50"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "الإيراد الفعلي المحقق (ر.س)" : "Actual Revenue (SAR)"}
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="100"
                    value={actualRevenue}
                    onChange={(e) => setActualRevenue(e.target.value)}
                    placeholder={ar ? "اتركه فارغاً إن لم يعرف بعد" : "Blank if unknown"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 font-semibold text-emerald-700"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "عدد العمليات / الفواتير" : "Transactions Count"}
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={actualVolume}
                    onChange={(e) => setActualVolume(e.target.value)}
                    placeholder={ar ? "لحساب متوسط الفاتورة" : "For AOV calc"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>

              {/* OPEX BREAKDOWN GRID */}
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200">
                <h4 className="font-bold text-slate-800 text-xs mb-3">
                  {ar ? "المصاريف التشغيلية الفعلية (ر.س - الحقول الفارغة تبقى غير محددة):" : "OPEX Breakdown (SAR):"}
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                  <div>
                    <label className="block text-[11px] text-slate-600 mb-1">{ar ? "الرواتب والتوطين" : "Salaries"}</label>
                    <input
                      type="number"
                      min="0"
                      value={actualSalaries}
                      onChange={(e) => setActualSalaries(e.target.value)}
                      placeholder="—"
                      className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-600 mb-1">{ar ? "الإيجار والموقع" : "Rent"}</label>
                    <input
                      type="number"
                      min="0"
                      value={actualRent}
                      onChange={(e) => setActualRent(e.target.value)}
                      placeholder="—"
                      className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-600 mb-1">{ar ? "المخزون والبضاعة" : "COGS"}</label>
                    <input
                      type="number"
                      min="0"
                      value={actualInventory}
                      onChange={(e) => setActualInventory(e.target.value)}
                      placeholder="—"
                      className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-600 mb-1">{ar ? "التسويق والإعلانات" : "Marketing"}</label>
                    <input
                      type="number"
                      min="0"
                      value={actualMarketing}
                      onChange={(e) => setActualMarketing(e.target.value)}
                      placeholder="—"
                      className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-600 mb-1">{ar ? "المرافق والرسوم" : "Utilities"}</label>
                    <input
                      type="number"
                      min="0"
                      value={actualUtilities}
                      onChange={(e) => setActualUtilities(e.target.value)}
                      placeholder="—"
                      className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "مصاريف رأسمالية (CAPEX)" : "CAPEX"}
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={actualCapex}
                    onChange={(e) => setActualCapex(e.target.value)}
                    placeholder="—"
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "الرصيد النقدي الختامي بالبنك" : "Closing Cash Balance"}
                  </label>
                  <input
                    type="number"
                    min="0"
                    value={actualClosingCash}
                    onChange={(e) => setActualClosingCash(e.target.value)}
                    placeholder={ar ? "لحساب المدرج المالي بدقة" : "For runway calc"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "مصدر البيانات" : "Source Type"}
                  </label>
                  <select
                    value={actualSourceType}
                    onChange={(e) => setActualSourceType(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 bg-white"
                  >
                    <option value="USER_ENTERED">{ar ? "إدخال يدوي للمؤسس" : "User Entered"}</option>
                    <option value="IMPORTED">{ar ? "ملف مستورد (CSV/Excel)" : "Imported"}</option>
                    <option value="SYSTEM_INTEGRATION">{ar ? "ربط نظامي (زاتكا/نقطة بيع)" : "System Integration"}</option>
                    <option value="DOCUMENT_BACKED">{ar ? "كشف حساب بنكي موثق" : "Document Backed"}</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "مرجع المصدر" : "Source Reference"}
                  </label>
                  <input
                    type="text"
                    value={actualSourceRef}
                    onChange={(e) => setActualSourceRef(e.target.value)}
                    placeholder={ar ? "رقم الفاتورة / الكشف" : "Invoice / Statement Ref"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  {ar ? "ملاحظات وتفسير الأداء" : "Notes"}
                </label>
                <input
                  type="text"
                  value={actualNotes}
                  onChange={(e) => setActualNotes(e.target.value)}
                  placeholder={ar ? "سياق ميداني للأداء في هذا الشهر..." : "Context notes..."}
                  className="w-full text-sm border border-slate-300 rounded-lg p-2"
                />
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={savingAction}
                  className="px-5 py-2 text-sm font-bold bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 transition"
                >
                  {savingAction ? (ar ? "جارٍ الحفظ..." : "Recording...") : ar ? "✓ تسجيل بيانات الفترة" : "✓ Record Period"}
                </button>
              </div>
            </form>
          </div>

          {/* RECORDED PERIODS HISTORY */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <h3 className="font-bold text-slate-900 text-sm">
                {ar ? "سجل الأشهر الفعلية المسجلة" : "Historical Recorded Periods"}
              </h3>
              <span className="text-xs font-semibold text-slate-600">
                {actualPeriods.length} {ar ? "فترات مسجلة" : "periods"}
              </span>
            </div>

            {actualPeriods.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">
                {ar ? "لم يتم تسجيل أي فترات تشغيلية بعد. استخدم النموذج أعلاه لتسجيل الشهر الأول." : "No actual periods recorded yet."}
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-right text-xs">
                  <thead className="bg-slate-100 text-slate-700 font-semibold border-b">
                    <tr>
                      <th className="p-3">الفترة</th>
                      <th className="p-3">الإيراد الفعلي</th>
                      <th className="p-3">المصاريف التشغيلية (OPEX)</th>
                      <th className="p-3">المصاريف الرأسمالية (CAPEX)</th>
                      <th className="p-3">صافي التدفق النقدي</th>
                      <th className="p-3">المصدر الموثق</th>
                      <th className="p-3">الملاحظات</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {actualPeriods.map((p) => (
                      <tr key={p.id} className="hover:bg-slate-50">
                        <td className="p-3 font-bold text-slate-800">{p.period_label}</td>
                        <td className="p-3 font-semibold text-emerald-700">
                          {p.actual_revenue !== null ? `${p.actual_revenue.toLocaleString()} ر.س` : "—"}
                        </td>
                        <td className="p-3 text-slate-700">
                          {p.total_actual_opex !== null && p.total_actual_opex !== undefined
                            ? `${p.total_actual_opex.toLocaleString()} ر.س`
                            : p.actual_opex !== null
                            ? `${p.actual_opex.toLocaleString()} ر.س`
                            : "—"}
                        </td>
                        <td className="p-3 text-slate-700">
                          {p.actual_capex !== null ? `${p.actual_capex.toLocaleString()} ر.س` : "—"}
                        </td>
                        <td className={`p-3 font-bold ${p.net_cashflow !== null && p.net_cashflow >= 0 ? "text-emerald-700" : "text-red-600"}`}>
                          {p.net_cashflow !== null ? `${p.net_cashflow.toLocaleString()} ر.س` : "—"}
                        </td>
                        <td className="p-3 text-slate-600">
                          <span className="bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">
                            {p.source_type || "USER_ENTERED"}
                          </span>
                          {p.source_reference && <div className="text-[10px] text-slate-400">{p.source_reference}</div>}
                        </td>
                        <td className="p-3 text-slate-500 max-w-xs truncate">{p.notes || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUBTAB 4: FORECAST VS ACTUAL VARIANCE MATRIX */}
      {subTab === "variances" && (
        <div className="space-y-6">
          {varianceSummary && (
            <>
              <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
                <div>
                  <span className="text-xs text-slate-500 font-medium">{ar ? "حالة الانحراف العامة للمشروع" : "Overall Variance Status"}</span>
                  <div className="mt-1 flex items-center gap-2">
                    {(() => {
                      const alert = alertLevelMap[varianceSummary.overall_health] || alertLevelMap.NORMAL;
                      return (
                        <span className={`px-3 py-1 text-xs font-bold rounded-full border ${alert.badge}`}>
                          {alert.ar}
                        </span>
                      );
                    })()}
                  </div>
                  <p className="text-xs text-slate-600 mt-1">{varianceSummary.summary_ar}</p>
                </div>
              </div>

              {/* DETAILED VARIANCE MATRIX TABLE */}
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                  <h3 className="font-bold text-slate-900 text-sm">
                    {ar ? "مصفوفة مقارنة خط الأساس مع الأداء الفعلي" : "Monthly Variance Matrix"}
                  </h3>
                  <span className="text-xs text-slate-500">
                    {ar ? "إذا غاب التوقع أو الفعلي يُعلن الانحراف كغير متوفر (NOT_AVAILABLE)" : "Missing side yields NOT_AVAILABLE"}
                  </span>
                </div>

                {!varianceSummary.period_variances || varianceSummary.period_variances.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 text-sm">
                    {ar ? "سجل فترات تشغيلية أولاً لمشاهدة تحليل الانحرافات." : "Record actual periods to see variance matrix."}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-right text-xs">
                      <thead className="bg-slate-100 text-slate-700 font-semibold border-b">
                        <tr>
                          <th className="p-3">الفترة</th>
                          <th className="p-3">الإيراد (توقع / فعلي)</th>
                          <th className="p-3">انحراف الإيراد</th>
                          <th className="p-3">المصاريف (توقع / فعلي)</th>
                          <th className="p-3">انحراف المصاريف</th>
                          <th className="p-3">التدفق النقدي</th>
                          <th className="p-3">مستوى التنبيه والتفسير</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-200">
                        {varianceSummary.period_variances.map((item: LaunchVarianceReport) => {
                          const alertMeta = alertLevelMap[item.alert] || alertLevelMap.NORMAL;
                          return (
                            <tr key={item.period_order} className="hover:bg-slate-50">
                              <td className="p-3 font-bold text-slate-800">{item.period_label}</td>
                              <td className="p-3">
                                <div>{item.actual?.revenue !== null ? `${item.actual.revenue.toLocaleString()} ر.س` : "—"}</div>
                                <div className="text-[11px] text-slate-400">
                                  توقع: {item.projected?.revenue !== null ? `${item.projected.revenue.toLocaleString()} ر.س` : "—"}
                                </div>
                              </td>
                              <td className="p-3">
                                {item.variance?.revenue_pct !== null && item.variance?.revenue_pct !== undefined ? (
                                  <>
                                    <span className={`font-semibold ${item.variance.revenue_diff && item.variance.revenue_diff >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                                      {item.variance.revenue_diff && item.variance.revenue_diff >= 0 ? "+" : ""}
                                      {item.variance.revenue_diff?.toLocaleString()} ر.س
                                    </span>
                                    <div className="text-[10px] text-slate-500">{item.variance.revenue_pct}%</div>
                                  </>
                                ) : (
                                  <span className="text-slate-400">—</span>
                                )}
                              </td>
                              <td className="p-3">
                                <div>{item.actual?.opex !== null ? `${item.actual.opex.toLocaleString()} ر.س` : "—"}</div>
                                <div className="text-[11px] text-slate-400">
                                  توقع: {item.projected?.opex !== null ? `${item.projected.opex.toLocaleString()} ر.س` : "—"}
                                </div>
                              </td>
                              <td className="p-3">
                                {item.variance?.opex_pct !== null && item.variance?.opex_pct !== undefined ? (
                                  <>
                                    <span className={`font-semibold ${item.variance.opex_diff && item.variance.opex_diff <= 0 ? "text-emerald-600" : "text-amber-600"}`}>
                                      {item.variance.opex_diff && item.variance.opex_diff >= 0 ? "+" : ""}
                                      {item.variance.opex_diff?.toLocaleString()} ر.س
                                    </span>
                                    <div className="text-[10px] text-slate-500">{item.variance.opex_pct}%</div>
                                  </>
                                ) : (
                                  <span className="text-slate-400">—</span>
                                )}
                              </td>
                              <td className={`p-3 font-bold ${item.actual?.net_cashflow !== null && item.actual.net_cashflow >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                                {item.actual?.net_cashflow !== null ? `${item.actual.net_cashflow.toLocaleString()} ر.س` : "—"}
                              </td>
                              <td className="p-3">
                                <span className={`px-2 py-0.5 text-[11px] font-bold rounded-full border ${alertMeta.badge}`}>
                                  {alertMeta.ar}
                                </span>
                                <div className="text-[10px] text-slate-500 mt-1 max-w-xs">{item.explanation_ar}</div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* SUBTAB 5: REFORECAST & RUNWAY */}
      {subTab === "reforecast" && (
        <div className="space-y-6">
          {/* RUNWAY & BREAK-EVEN BANNER */}
          {latestReforecast && (
            <div className="bg-gradient-to-l from-indigo-50 via-white to-slate-50 border border-indigo-200 rounded-xl p-6 shadow-sm">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-indigo-600 text-white">
                      {latestReforecast.version || `v${latestReforecast.version_number}`}
                    </span>
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-800 border border-amber-200">
                      USER_ASSUMPTION
                    </span>
                    <span className="text-xs text-slate-500">
                      {latestReforecast.reforecast_title}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900">
                    {ar ? "مؤشرات السيولة ومدرج النجاة المالي (Cash Runway)" : "Cash Runway & Break-Even Metrics"}
                  </h3>
                  <p className="text-xs text-slate-600 mt-1">{latestReforecast.adjustment_rationale}</p>
                </div>

                <div className="flex flex-wrap items-center gap-6">
                  <div className="text-right">
                    <span className="text-xs text-slate-500">{ar ? "معدل الحرق الشهري الفعلي" : "Monthly Burn Rate"}</span>
                    <p className="text-lg font-bold text-red-600">
                      {latestReforecast.monthly_burn_rate !== null ? `${latestReforecast.monthly_burn_rate.toLocaleString()} ر.س/شهر` : "—"}
                    </p>
                  </div>
                  <div className="text-right border-r pr-6 border-slate-200">
                    <span className="text-xs text-slate-500">{ar ? "مدرج السيولة المتبقي" : "Estimated Runway"}</span>
                    <p className="text-xl font-black text-indigo-700">
                      {latestReforecast.remaining_runway_months !== null ? `${latestReforecast.remaining_runway_months} شهر` : (ar ? "غير متوفر (يلزم رصيد كاش)" : "NOT_AVAILABLE")}
                    </p>
                  </div>
                  <div className="text-right border-r pr-6 border-slate-200">
                    <span className="text-xs text-slate-500">{ar ? "شهر التدفق الإيجابي" : "Cash Flow Positive"}</span>
                    <p className="text-base font-bold text-emerald-700">
                      {latestReforecast.cash_flow_positive_month ? `الشهر M${latestReforecast.cash_flow_positive_month}` : (ar ? "لم يتحقق بعد" : "Pending")}
                    </p>
                  </div>
                  <div className="text-right border-r pr-6 border-slate-200">
                    <span className="text-xs text-slate-500">{ar ? "شهر استرداد الاستثمار (التعادل)" : "Break-Even Month"}</span>
                    <p className="text-base font-bold text-purple-700">
                      {latestReforecast.financial_break_even_month ? `الشهر M${latestReforecast.financial_break_even_month}` : (ar ? "لم يتحقق بعد" : "Pending")}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TRIGGER REFORECAST FORM */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
            <h3 className="font-bold text-slate-900 text-sm mb-1">
              {ar ? "توليد سيناريو إعادة التنبؤ المالي (افتراضات معلنة للمؤسس)" : "Generate Dynamic Reforecast"}
            </h3>
            <p className="text-xs text-slate-600 mb-4">
              {ar
                ? "يتم وسم الافتراضات صراحة كـ USER_ASSUMPTION. لا يتم التعامل مع إجمالي الاستثمار كرصيد نقدي."
                : "Assumptions tagged as USER_ASSUMPTION. Total investment is never equated to cash balance."}
            </p>

            <form onSubmit={handleCreateReforecast} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "عنوان السيناريو" : "Scenario Title"}
                  </label>
                  <input
                    type="text"
                    required
                    value={reforecastTitle}
                    onChange={(e) => setReforecastTitle(e.target.value)}
                    placeholder={ar ? "مثال: السيناريو المتحفظ بعد أول شهرين" : "e.g. Conservative Scenario"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "مبررات وأسباب التعديل" : "Adjustment Rationale"}
                  </label>
                  <input
                    type="text"
                    required
                    value={reforecastReason}
                    onChange={(e) => setReforecastReason(e.target.value)}
                    placeholder={ar ? "مثال: تعديل بناء على استجابة العملاء في الشهر الأول" : "e.g. Adjusted based on M01 actuals"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "الرصيد النقدي الفعلي بالبنك (ر.س - اختياري)" : "Explicit Cash Balance (Optional)"}
                  </label>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    value={reforecastCashBalance}
                    onChange={(e) => setReforecastCashBalance(e.target.value)}
                    placeholder={ar ? "اتركه فارغاً للاعتماد على رصيد الفعليات" : "Leave blank to use actuals closing cash"}
                    className="w-full text-sm border border-slate-300 rounded-lg p-2 font-bold text-slate-900"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "تعديل وتيرة نمو الإيراد (% - مثال: 5 أو -10)" : "Revenue Growth Rate Adjustment %"}
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={reforecastRevAdj}
                    onChange={(e) => setReforecastRevAdj(e.target.value)}
                    placeholder="e.g. 5.0 or -10.0"
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    {ar ? "تعديل التكاليف التشغيلية (% - مثال: 2 أو -5)" : "OPEX Adjustment %"}
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    value={reforecastCostAdj}
                    onChange={(e) => setReforecastCostAdj(e.target.value)}
                    placeholder="e.g. 2.0 or -5.0"
                    className="w-full text-sm border border-slate-300 rounded-lg p-2"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={savingAction || !reforecastTitle}
                  className="px-5 py-2 text-sm font-bold bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition"
                >
                  {savingAction ? (ar ? "جارٍ الحساب..." : "Generating...") : ar ? "⚡ توليد سيناريو إعادة التنبؤ" : "⚡ Generate Reforecast"}
                </button>
              </div>
            </form>
          </div>

          {/* REFORECAST PROJECTIONS TABLE */}
          {latestReforecast?.reforecast_payload?.monthly_projections && (
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
              <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
                <h3 className="font-bold text-slate-900 text-sm">
                  {ar ? `مسار التوقعات المحدثة (${latestReforecast.version || `v${latestReforecast.version_number}`})` : `Updated Projection Trajectory`}
                </h3>
                <span className="text-xs text-slate-500 font-medium">12 {ar ? "شهر قادم" : "Months Forward"}</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-right text-xs">
                  <thead className="bg-slate-100 text-slate-700 font-semibold border-b">
                    <tr>
                      <th className="p-3">الفترة</th>
                      <th className="p-3">الإيراد المتوقع المحدث</th>
                      <th className="p-3">المصاريف المتوقعة</th>
                      <th className="p-3">صافي التدفق الشهري</th>
                      <th className="p-3">صافي التدفق التراكمي</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {latestReforecast.reforecast_payload.monthly_projections.map((sp: any) => (
                      <tr key={sp.month} className="hover:bg-slate-50">
                        <td className="p-3 font-bold text-slate-800">{sp.period_label}</td>
                        <td className="p-3 font-semibold text-emerald-700">
                          {sp.reforecast_revenue !== null ? `${sp.reforecast_revenue.toLocaleString()} ر.س` : "—"}
                        </td>
                        <td className="p-3 text-slate-700">
                          {sp.reforecast_opex !== null ? `${sp.reforecast_opex.toLocaleString()} ر.س` : "—"}
                        </td>
                        <td className={`p-3 font-bold ${sp.reforecast_net_cashflow !== null && sp.reforecast_net_cashflow >= 0 ? "text-emerald-700" : "text-red-600"}`}>
                          {sp.reforecast_net_cashflow !== null ? `${sp.reforecast_net_cashflow.toLocaleString()} ر.س` : "—"}
                        </td>
                        <td className={`p-3 font-bold ${sp.cumulative_net_cashflow !== null && sp.cumulative_net_cashflow !== undefined && sp.cumulative_net_cashflow >= 0 ? "text-slate-800" : "text-red-600"}`}>
                          {sp.cumulative_net_cashflow !== null && sp.cumulative_net_cashflow !== undefined ? `${sp.cumulative_net_cashflow.toLocaleString()} ر.س` : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
