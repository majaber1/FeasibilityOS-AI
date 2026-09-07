"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  getFinancingStructure,
  FinancingStructure,
  FinancingSourceItem,
  FinancingUseItem,
  FinancingProgramAllocation,
  FinancingWarning,
  FinancingNextAction,
} from "@/lib/api";

interface Props {
  token: string;
  studyId: number;
  period?: string;
  refreshSignal?: number;
}

export default function FinancingStructureSection({ token, studyId, period, refreshSignal }: Props) {
  const [data, setData] = useState<FinancingStructure | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getFinancingStructure(token, studyId, period);
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load financing structure";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [token, studyId, period]);

  useEffect(() => {
    fetchData();
  }, [fetchData, refreshSignal]);

  const formatCurrency = (val?: number | null) => {
    if (val === null || val === undefined) return "—";
    return `${val.toLocaleString()} ر.س`;
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-rose-500/10 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800";
      case "WARNING":
        return "bg-amber-500/10 text-amber-700 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800";
      case "ADVISORY":
      default:
        return "bg-blue-500/10 text-blue-700 border-blue-300 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-800";
    }
  };

  const getActionStatusBadge = (status: string) => {
    switch (status) {
      case "READY":
        return { label: "مكتمل وجاهز", className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300" };
      case "ACTION_REQUIRED":
        return { label: "إجراء مطلوب", className: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300" };
      case "PENDING_VALUATION":
        return { label: "بانتظار التقييم", className: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300" };
      case "MATCHED_PROGRAM":
        return { label: "برنامج مطابق للفحص الأولي", className: "bg-primary/10 text-primary dark:bg-primary/20" };
      case "POTENTIAL_SOURCE":
        return { label: "مصدر تمويل محتمل", className: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300" };
      default:
        return { label: status, className: "bg-muted text-muted-foreground" };
    }
  };

  return (
    <section id="financing-structure-section" className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-xl font-bold text-foreground">هيكل التمويل ومصادر واستخدامات الأموال</h3>
            <span className="text-xs bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 px-2.5 py-0.5 rounded-full font-medium">
              Phase 20 • Wave 2 Capstone
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Reconciled Sources & Uses of Funds — نموذج مالي متكامل لتوزيع مصادر رأس المال وخيارات التمويل التنموي
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-background hover:bg-muted transition text-foreground self-start md:self-auto"
        >
          {loading ? "جاري الحساب..." : "إعادة الاحتساب"}
        </button>
      </div>

      {/* Mandatory Regulatory Disclaimer */}
      <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs leading-relaxed space-y-1">
        <p className="font-semibold flex items-center gap-1.5">
          <span>⚠️</span> إخلاء مسؤولية تنظيمي معتمد:
        </p>
        <p>{data?.disclaimer_ar || "هيكل التمويل ومصادر واستخدامات الأموال المعروضة هي نموذج استرشادي مبني على القواعد المعلنة واشتراطات الملاءة المالية، ولا تمثل موافقة تمويلية أو التزاماً بنكياً."}</p>
        <p className="text-[11px] text-muted-foreground">{data?.disclaimer_en}</p>
      </div>

      {/* Loading & Error States */}
      {loading && !data && (
        <div className="py-12 text-center text-muted-foreground animate-pulse">
          جاري احتساب هيكل التمويل ومصادر الأموال...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm">
          {error}
        </div>
      )}

      {data && (
        <>
          {/* KPI Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-lg border border-border bg-muted/20">
              <span className="text-xs text-muted-foreground block">إجمالي الاحتياج الاستثماري</span>
              <span className="text-lg font-bold text-foreground mt-0.5 block">
                {formatCurrency(data.total_project_requirement)}
              </span>
              <span className="text-[10px] text-muted-foreground">100% استخدامات الأموال (Uses)</span>
            </div>

            <div className="p-3.5 rounded-lg border border-emerald-500/30 bg-emerald-50/40 dark:bg-emerald-950/20">
              <span className="text-xs text-emerald-800 dark:text-emerald-300 block">المساهمة الذاتية (مصادر مؤكدة)</span>
              <span className="text-lg font-bold text-emerald-700 dark:text-emerald-300 mt-0.5 block">
                {formatCurrency(data.owner_equity)}
              </span>
              <span className="text-[10px] text-emerald-700/80 dark:text-emerald-400">
                {(data.equity_percentage * 100).toFixed(1)}% من إجمالي المشروع
              </span>
            </div>

            <div className="p-3.5 rounded-lg border border-border bg-muted/20">
              <span className="text-xs text-muted-foreground block">فجوة التمويل المؤكدة (Confirmed Gap)</span>
              <span className="text-lg font-bold text-foreground mt-0.5 block">
                {formatCurrency(data.confirmed_funding_gap ?? (data.total_project_requirement - (data.total_confirmed_sources ?? data.owner_equity)))}
              </span>
              <span className="text-[10px] text-muted-foreground">
                الاحتياج ناقص المصادر المؤكدة
              </span>
            </div>

            <div className={`p-3.5 rounded-lg border ${
              (data.potential_residual_gap ?? data.residual_gap) > 0
                ? "border-rose-500/40 bg-rose-50/40 dark:bg-rose-950/20"
                : "border-emerald-500/30 bg-emerald-50/40 dark:bg-emerald-950/20"
            }`}>
              <span className={`text-xs block ${(data.potential_residual_gap ?? data.residual_gap) > 0 ? "text-rose-800 dark:text-rose-300" : "text-emerald-800 dark:text-emerald-300"}`}>
                الفجوة المتبقية المحتملة (Potential Residual)
              </span>
              <span className={`text-lg font-bold mt-0.5 block ${(data.potential_residual_gap ?? data.residual_gap) > 0 ? "text-rose-700 dark:text-rose-400" : "text-emerald-700 dark:text-emerald-300"}`}>
                {formatCurrency(data.potential_residual_gap ?? data.residual_gap)}
              </span>
              <span className="text-[10px] text-muted-foreground">
                {(data.potential_residual_gap ?? data.residual_gap) > 0 ? "غير مغطاة بعد الفحص الاسترشادي" : "تمت تغطية كامل الاحتياج"}
              </span>
            </div>
          </div>

          {/* Internal Screening Debt Capacity Strip */}
          <div className="p-3 rounded-lg bg-blue-50/50 dark:bg-blue-950/20 border border-blue-200 dark:border-blue-900 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="font-bold text-blue-900 dark:text-blue-300">طاقة الاستدانة التقديرية (فحص داخلي استرشادي):</span>
              <span className="font-mono font-bold text-foreground">{formatCurrency(data.safe_debt_capacity)}</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                حالة الفحص: {data.capacity_status}
              </span>
            </div>
            <span className="text-[10px] text-muted-foreground">
              تقدير داخلي مبني على التدفقات؛ لا يمثل موافقة ائتمانية بنكية.
            </span>
          </div>

          {/* Credit Enhancement / Guarantee Support Card (Separated from Cash Debt) */}
          {data.credit_enhancements && data.credit_enhancements.length > 0 && (
            <div className="p-4 rounded-lg bg-purple-50/40 dark:bg-purple-950/20 border border-purple-300 dark:border-purple-800 space-y-3">
              <div className="flex items-center justify-between border-b border-purple-200 dark:border-purple-800/60 pb-2">
                <div className="flex items-center gap-2">
                  <span className="text-base">🛡️</span>
                  <h4 className="font-bold text-sm text-purple-950 dark:text-purple-200">
                    دعم الضمانات والتعزيز الائتماني (Credit Enhancement / Guarantee Support)
                  </h4>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200 font-medium">
                  مساهمة نقدية مباشرة: 0 ر.س
                </span>
              </div>
              <p className="text-xs text-purple-900/80 dark:text-purple-300 leading-relaxed">
                برامج الضمانات (مثل برنامج كفالة) لا تقدم سيولة نقدية مباشرة لمصادر واستخدامات الأموال، وإنما توفر كفالات ائتمانية للبنوك التجارية لتغطية مخاطر التمويل وتقليل متطلبات الرهن العيني لتسهيل الإقراض البنكي.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                {data.credit_enhancements.map((ce) => (
                  <div key={ce.program_id} className="p-3 rounded-lg border border-purple-200 dark:border-purple-800 bg-background/80 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-foreground">{ce.program_name_ar}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                        {ce.provider}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground">{ce.role_ar}</p>
                    <div className="flex items-center justify-between text-[11px] pt-1">
                      <span className="text-muted-foreground">الحد الأقصى للضمان:</span>
                      <span className="font-bold text-foreground">{formatCurrency(ce.max_guarantee_amount)}</span>
                    </div>
                    {ce.official_source_url && (
                      <div className="pt-1 text-end">
                        <a href={ce.official_source_url} target="_blank" rel="noopener noreferrer" className="text-[11px] text-primary hover:underline">
                          البوابة الرسمية لكفالة ↗
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sources & Uses Reconciled Table / Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Uses of Funds */}
            <div className="p-4 rounded-lg border border-border bg-card space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <h4 className="font-bold text-sm text-foreground">استخدامات الأموال (Uses of Funds)</h4>
                <span className="text-xs font-semibold text-foreground">{formatCurrency(data.total_project_requirement)}</span>
              </div>
              <div className="space-y-2.5">
                {data.uses.map((u: FinancingUseItem) => (
                  <div key={u.category_key} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-foreground">{u.name_ar}</span>
                      <span className="font-mono text-muted-foreground">{formatCurrency(u.amount)} ({u.percentage}%)</span>
                    </div>
                    <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-primary rounded-full" style={{ width: `${u.percentage}%` }} />
                    </div>
                    <span className="text-[10px] text-muted-foreground block">{u.name_en}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Sources of Funds */}
            <div className="p-4 rounded-lg border border-border bg-card space-y-3">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <h4 className="font-bold text-sm text-foreground">مصادر التمويل (Sources of Funds)</h4>
                <span className="text-xs font-semibold text-foreground">{formatCurrency(data.total_identified_sources)}</span>
              </div>
              <div className="space-y-2.5">
                {data.sources.map((s: FinancingSourceItem) => {
                  const barColor =
                    s.source_type === "EQUITY"
                      ? "bg-emerald-500"
                      : s.source_type === "EXISTING_DEBT"
                      ? "bg-blue-500"
                      : s.source_type === "PROGRAM_DEBT"
                      ? "bg-sky-500"
                      : "bg-rose-500";
                  return (
                    <div key={s.source_key} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-foreground">{s.name_ar}</span>
                        <span className="font-mono text-muted-foreground">{formatCurrency(s.amount)} ({s.percentage}%)</span>
                      </div>
                      <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                        <div className={`h-full ${barColor} rounded-full`} style={{ width: `${s.percentage}%` }} />
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                        <span>{s.name_en}</span>
                        {s.official_source_url && (
                          <a href={s.official_source_url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                            المصدر ↗
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Capital Structure Ratios Bar */}
          <div className="p-4 rounded-lg bg-muted/30 border border-border space-y-2">
            <h4 className="font-bold text-xs text-foreground uppercase tracking-wider">مؤشرات هيكل رأس المال والتحوط</h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-2.5 rounded bg-background border border-border/60">
                <span className="text-muted-foreground block text-[11px]">نسبة المساهمة الذاتية</span>
                <span className="font-bold text-foreground text-sm">{(data.equity_percentage * 100).toFixed(1)}%</span>
                <span className="text-[10px] text-muted-foreground block">(فرضية فحص داخلي: 20%)</span>
              </div>
              <div className="p-2.5 rounded bg-background border border-border/60">
                <span className="text-muted-foreground block text-[11px]">نسبة الدين إلى التكلفة</span>
                <span className="font-bold text-foreground text-sm">{(data.debt_percentage * 100).toFixed(1)}%</span>
                <span className="text-[10px] text-muted-foreground block">(Debt-to-Cost)</span>
              </div>
              <div className="p-2.5 rounded bg-background border border-border/60">
                <span className="text-muted-foreground block text-[11px]">معدل الرافعة المالية (D/E)</span>
                <span className="font-bold text-foreground text-sm">
                  {data.debt_to_equity_ratio !== null ? `${data.debt_to_equity_ratio}x` : "—"}
                </span>
                <span className="text-[10px] text-muted-foreground block">(Debt to Equity)</span>
              </div>
              <div className="p-2.5 rounded bg-background border border-border/60">
                <span className="text-muted-foreground block text-[11px]">تغطية الضمانات العينية</span>
                <span className="font-bold text-foreground text-sm">
                  {(data.collateral_coverage_ratio * 100).toFixed(1)}%
                </span>
                <span className="text-[10px] text-muted-foreground block">(من إجمالي التمويل المطلوب)</span>
              </div>
            </div>
          </div>

          {/* Program Allocations Cards */}
          {data.program_allocations.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-sm text-foreground">خيارات البرامج التمويلية المقترحة (Screening Options)</h4>
                <span className="text-[11px] text-muted-foreground">خيارات استرشادية لا تمثل تمويلاً معتمداً</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.program_allocations.map((pa: FinancingProgramAllocation) => (
                  <div key={pa.program_id} className="p-3.5 rounded-lg border border-border bg-card space-y-2 text-xs">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-muted text-muted-foreground">
                          {pa.provider}
                        </span>
                        <h5 className="font-bold text-foreground text-sm mt-1">{pa.program_name_ar}</h5>
                        <p className="text-[11px] text-muted-foreground">{pa.program_name_en}</p>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                        pa.match_status === "MATCH"
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300"
                          : "bg-amber-50 text-amber-800 border border-amber-300 dark:bg-amber-950 dark:text-amber-300"
                      }`}>
                        {pa.match_status === "MATCH" ? "برنامج مطابق للفحص الأولي" : "مطابقة محتملة (تتطلب تحقق)"}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 p-2 rounded bg-muted/20 border border-border/30">
                      <div>
                        <span className="text-muted-foreground block text-[10px]">المبلغ المخصص المقترح</span>
                        <span className="font-bold text-primary text-xs">
                          {pa.allocation_status === "CREDIT_ENHANCEMENT_ONLY"
                            ? "تعزيز ائتماني (0 ر.س نقد)"
                            : pa.allocation_status === "CAPACITY_NOT_EVALUATED"
                            ? "غير محدد (لم تُحسب الطاقة الاستيعابية)"
                            : pa.allocated_amount !== null && pa.allocated_amount !== undefined
                            ? formatCurrency(pa.allocated_amount)
                            : "غير محدد (يتطلب مراجعة الحد)"}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground block text-[10px]">المدة والسماح</span>
                        <span className="font-semibold text-foreground text-xs">
                          {pa.term_months ? `${pa.term_months} شهر` : "—"}
                          {pa.grace_period_months ? ` (${pa.grace_period_months} سماح)` : ""}
                        </span>
                      </div>
                    </div>

                    {pa.official_source_url && (
                      <div className="pt-1 text-end">
                        <a href={pa.official_source_url} target="_blank" rel="noopener noreferrer" className="text-[11px] text-primary hover:underline">
                          بوابة التقديم الرسمية لدى {pa.provider} ↗
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Warnings & Alerts */}
          {data.warnings.length > 0 && (
            <div className="space-y-2">
              <h4 className="font-bold text-sm text-foreground">تنبيهات وملاحظات هيكل التمويل</h4>
              <div className="space-y-2">
                {data.warnings.map((w: FinancingWarning) => (
                  <div
                    key={w.code}
                    className={`p-3 rounded-lg border text-xs leading-relaxed space-y-1 ${getSeverityBadge(w.severity)}`}
                  >
                    <div className="font-bold flex items-center gap-1.5">
                      <span>{w.severity === "CRITICAL" ? "🔴" : w.severity === "WARNING" ? "🟡" : "ℹ️"}</span>
                      <span>{w.title_ar}</span>
                      <span className="text-[11px] font-normal text-muted-foreground">({w.title_en})</span>
                    </div>
                    <p>{w.message_ar}</p>
                    <p className="text-[11px] text-muted-foreground">{w.message_en}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sequential Next Actions Checklist */}
          <div id="next-actions-section" className="space-y-3 pt-4 border-t border-border">
            <h4 className="font-bold text-sm text-foreground">خطة الإجراءات والخطوات القادمة (Next Actions Roadmap)</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {data.next_actions.map((act: FinancingNextAction) => {
                const sBadge = getActionStatusBadge(act.status);
                return (
                  <div key={act.step_number} className="p-3.5 rounded-lg border border-border bg-card space-y-1.5 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-foreground">
                        الخطوة {act.step_number}: {act.title_ar}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${sBadge.className}`}>
                        {sBadge.label}
                      </span>
                    </div>
                    <p className="text-muted-foreground text-[11px]">{act.title_en}</p>
                    <p className="text-foreground text-[11px] pt-1 border-t border-border/40">{act.description_ar}</p>
                    <p className="text-muted-foreground text-[10px]">{act.description_en}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
