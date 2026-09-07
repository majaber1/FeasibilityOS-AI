"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  getFundingMatches,
  FundingMatchesSummary,
  FundingProgramMatchResult,
  FundingRuleEvaluation,
} from "@/lib/api";

interface Props {
  token: string;
  studyId: number;
  period?: string;
  refreshSignal?: number;
}

type StatusFilter = "ALL" | "MATCH" | "POSSIBLE_MATCH" | "NEEDS_INFORMATION" | "NOT_MATCHED";

export default function FundingMatchesSection({ token, studyId, period, refreshSignal }: Props) {
  const [data, setData] = useState<FundingMatchesSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [selectedProgram, setSelectedProgram] = useState<FundingProgramMatchResult | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getFundingMatches(token, studyId, period);
      setData(res);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load funding matches";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [token, studyId, period]);

  useEffect(() => {
    fetchData();
  }, [fetchData, refreshSignal]);

  const filteredMatches = data?.matches.filter((m) => {
    if (statusFilter === "ALL") return true;
    return m.overall_match_status === statusFilter;
  }) ?? [];

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "MATCH":
        return {
          labelAr: "مطابق للشروط",
          labelEn: "MATCH",
          className: "bg-emerald-100 text-emerald-800 border-emerald-300 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800",
        };
      case "POSSIBLE_MATCH":
        return {
          labelAr: "مطابقة محتملة",
          labelEn: "POSSIBLE MATCH",
          className: "bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800",
        };
      case "NEEDS_INFORMATION":
        return {
          labelAr: "بيانات ناقصة",
          labelEn: "NEEDS INFO",
          className: "bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-950 dark:text-blue-300 dark:border-blue-800",
        };
      case "NOT_MATCHED":
        return {
          labelAr: "غير مطابق",
          labelEn: "NOT MATCHED",
          className: "bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950 dark:text-rose-300 dark:border-rose-800",
        };
      default:
        return {
          labelAr: status,
          labelEn: status,
          className: "bg-gray-100 text-gray-800 border-gray-300 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700",
        };
    }
  };

  const getRuleResultBadge = (result: string) => {
    switch (result) {
      case "PASS":
        return {
          label: "مستوفى PASS",
          className: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800",
        };
      case "FAIL":
        return {
          label: "غير مستوفى FAIL",
          className: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800",
        };
      case "UNKNOWN":
      default:
        return {
          label: "يحتاج تدقيق UNKNOWN",
          className: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800",
        };
    }
  };

  const formatCurrency = (val?: number | null) => {
    if (val === null || val === undefined) return "—";
    return `${val.toLocaleString()} ر.س`;
  };

  return (
    <section id="funding-matches-section" className="rounded-xl border border-border bg-card p-6 shadow-sm space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-xl font-bold text-foreground">مطابقة البرامج التمويلية المعتمدة</h3>
            <span className="text-xs bg-primary/10 text-primary px-2.5 py-0.5 rounded-full font-medium">
              Phase 19 • Deterministic Matching
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Verified Funding Program Matching Engine — فحص آلي دقيق لقواعد الأهلية وفق البيانات المعتمدة
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="px-3 py-1.5 text-xs font-medium rounded-lg border border-border bg-background hover:bg-muted transition text-foreground self-start md:self-auto"
        >
          {loading ? "جاري التحديث..." : "إعادة الفحص"}
        </button>
      </div>

      {/* Mandatory Regulatory Disclaimer */}
      <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs leading-relaxed space-y-1">
        <p className="font-semibold flex items-center gap-1.5">
          <span>⚠️</span> إخلاء مسؤولية تنظيمي معتمد:
        </p>
        <p>{data?.disclaimer_ar || "نتائج المطابقة هي فحص آلي استرشادي مبني على القواعد المعتمدة المعلنة من الجهات التمويلية في المملكة العربية السعودية، ولا تشكل موافقة ائتمانية أو التزاماً بالتمويل."}</p>
        <p className="text-[11px] text-muted-foreground">{data?.disclaimer_en}</p>
      </div>

      {/* Loading & Error States */}
      {loading && !data && (
        <div className="py-12 text-center text-muted-foreground animate-pulse">
          جاري مطابقة اشتراطات التمويل مع البرامج المعتمدة...
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/30 text-destructive text-sm">
          {error}
        </div>
      )}

      {data && (
        <>
          {/* Study Snapshot Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 p-4 rounded-lg bg-muted/40 border border-border/60 text-xs">
            <div>
              <span className="text-muted-foreground block">القطاع / النشاط</span>
              <span className="font-semibold text-foreground">{data.study_profile_snapshot.sector || "غير محدد"}</span>
            </div>
            <div>
              <span className="text-muted-foreground block">مرحلة المشروع</span>
              <span className="font-semibold text-foreground uppercase">{data.study_profile_snapshot.stage || "STARTUP"}</span>
            </div>
            <div>
              <span className="text-muted-foreground block">إجمالي التكلفة</span>
              <span className="font-semibold text-foreground">{formatCurrency(data.study_profile_snapshot.total_project_requirement)}</span>
            </div>
            <div>
              <span className="text-muted-foreground block">المساهمة الذاتية</span>
              <span className="font-semibold text-foreground">{formatCurrency(data.study_profile_snapshot.owner_contribution)}</span>
            </div>
            <div>
              <span className="text-muted-foreground block">الفجوة التمويلية</span>
              <span className="font-bold text-primary">{formatCurrency(data.study_profile_snapshot.funding_gap)}</span>
            </div>
            <div>
              <span className="text-muted-foreground block">الضمانات المتاحة</span>
              <span className="font-semibold text-foreground">
                {formatCurrency(data.study_profile_snapshot.available_collateral)}
                {data.study_profile_snapshot.funding_gap > 0 && (
                  <span className="text-[10px] text-muted-foreground block">
                    ({(data.study_profile_snapshot.collateral_coverage_ratio * 100).toFixed(0)}% تغطية)
                  </span>
                )}
              </span>
            </div>
          </div>

          {/* KPI Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div
              onClick={() => setStatusFilter("ALL")}
              className={`cursor-pointer p-3 rounded-lg border text-center transition ${
                statusFilter === "ALL" ? "border-primary bg-primary/5 ring-1 ring-primary" : "border-border bg-card hover:bg-muted/30"
              }`}
            >
              <div className="text-2xl font-bold text-foreground">{data.total_programs_evaluated}</div>
              <div className="text-xs text-muted-foreground mt-0.5">البرامج المفحوصة</div>
            </div>

            <div
              onClick={() => setStatusFilter("MATCH")}
              className={`cursor-pointer p-3 rounded-lg border text-center transition ${
                statusFilter === "MATCH" ? "border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/30 ring-1 ring-emerald-500" : "border-border bg-card hover:bg-muted/30"
              }`}
            >
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{data.matches_count}</div>
              <div className="text-xs text-muted-foreground mt-0.5">مطابق تماماً (MATCH)</div>
            </div>

            <div
              onClick={() => setStatusFilter("POSSIBLE_MATCH")}
              className={`cursor-pointer p-3 rounded-lg border text-center transition ${
                statusFilter === "POSSIBLE_MATCH" ? "border-amber-500 bg-amber-50/50 dark:bg-amber-950/30 ring-1 ring-amber-500" : "border-border bg-card hover:bg-muted/30"
              }`}
            >
              <div className="text-2xl font-bold text-amber-600 dark:text-amber-400">{data.possible_matches_count}</div>
              <div className="text-xs text-muted-foreground mt-0.5">مطابقة محتملة</div>
            </div>

            <div
              onClick={() => setStatusFilter("NEEDS_INFORMATION")}
              className={`cursor-pointer p-3 rounded-lg border text-center transition ${
                statusFilter === "NEEDS_INFORMATION" ? "border-blue-500 bg-blue-50/50 dark:bg-blue-950/30 ring-1 ring-blue-500" : "border-border bg-card hover:bg-muted/30"
              }`}
            >
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{data.needs_information_count}</div>
              <div className="text-xs text-muted-foreground mt-0.5">بيانات ناقصة</div>
            </div>

            <div
              onClick={() => setStatusFilter("NOT_MATCHED")}
              className={`cursor-pointer p-3 rounded-lg border text-center transition ${
                statusFilter === "NOT_MATCHED" ? "border-rose-500 bg-rose-50/50 dark:bg-rose-950/30 ring-1 ring-rose-500" : "border-border bg-card hover:bg-muted/30"
              }`}
            >
              <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">{data.not_matched_count}</div>
              <div className="text-xs text-muted-foreground mt-0.5">غير مطابق</div>
            </div>
          </div>

          {/* Program Cards Grid */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                عرض {filteredMatches.length} من أصل {data.total_programs_evaluated} برنامج
              </span>
              {statusFilter !== "ALL" && (
                <button
                  onClick={() => setStatusFilter("ALL")}
                  className="text-primary hover:underline"
                >
                  إلغاء التصفية
                </button>
              )}
            </div>

            {filteredMatches.length === 0 ? (
              <div className="py-8 text-center text-muted-foreground text-sm border border-dashed rounded-lg">
                لا توجد برامج تطابق التصفية الحالية ({statusFilter}).
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredMatches.map((m) => {
                  const badge = getStatusBadge(m.overall_match_status);
                  return (
                    <div
                      key={m.program_id}
                      className="rounded-lg border border-border bg-card p-4 hover:border-primary/50 transition shadow-xs flex flex-col justify-between space-y-3"
                    >
                      <div>
                        {/* Top: Provider & Match Status */}
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-muted text-muted-foreground">
                              {m.provider}
                            </span>
                            <span className="text-xs text-muted-foreground">{m.provider_ar}</span>
                          </div>
                          <span
                            className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${badge.className}`}
                          >
                            {badge.labelAr}
                          </span>
                        </div>

                        {/* Program Name */}
                        <div className="mt-2">
                          <h4 className="font-bold text-foreground text-base leading-snug">
                            {m.program_name_ar}
                          </h4>
                          <p className="text-xs text-muted-foreground mt-0.5">{m.program_name_en}</p>
                        </div>

                        {/* Status Reason */}
                        <div className="mt-2 p-2 rounded bg-muted/30 border border-border/50 text-xs">
                          <p className="text-foreground">{m.status_reason_ar}</p>
                          <p className="text-[11px] text-muted-foreground mt-0.5">{m.status_reason_en}</p>
                        </div>

                        {/* Terms Pill Grid */}
                        <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                          <div className="bg-muted/20 p-2 rounded border border-border/40">
                            <span className="text-muted-foreground block text-[11px]">سقف التمويل</span>
                            <span className="font-semibold text-foreground">
                              {m.financing_max ? formatCurrency(m.financing_max) : "غير محدد"}
                            </span>
                          </div>
                          <div className="bg-muted/20 p-2 rounded border border-border/40">
                            <span className="text-muted-foreground block text-[11px]">المدة والسماح</span>
                            <span className="font-semibold text-foreground">
                              {m.term_months ? `${m.term_months} شهر` : "—"}
                              {m.grace_period_months ? ` (سماح ${m.grace_period_months})` : ""}
                            </span>
                          </div>
                        </div>

                        {/* Rules Summary Pills */}
                        <div className="mt-3 flex flex-wrap gap-1.5 text-[11px]">
                          <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-medium">
                            {m.passed_rules.length} شروط مستوفاة
                          </span>
                          {m.failed_rules.length > 0 && (
                            <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-700 dark:text-rose-300 font-medium">
                              {m.failed_rules.length} شروط غير مستوفاة
                            </span>
                          )}
                          {m.unknown_rules.length > 0 && (
                            <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-700 dark:text-amber-300 font-medium">
                              {m.unknown_rules.length} اشتراطات قيد التحقق
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Bottom Action */}
                      <div className="pt-2 border-t border-border/50 flex items-center justify-between">
                        <span className="text-[11px] text-muted-foreground">
                          إصدار القاعدة: v{m.rule_version}
                        </span>
                        <button
                          onClick={() => setSelectedProgram(m)}
                          className="px-3 py-1 text-xs font-semibold rounded bg-primary text-primary-foreground hover:bg-primary/90 transition"
                        >
                          عرض تفاصيل القواعد والأدلة ←
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}

      {/* Rule-by-Rule Reasoning Modal */}
      {selectedProgram && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto"
          onClick={() => setSelectedProgram(null)}
        >
          <div
            className="bg-card border border-border rounded-xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="p-5 border-b border-border flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 text-xs rounded bg-muted text-muted-foreground font-semibold">
                    {selectedProgram.provider}
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                      getStatusBadge(selectedProgram.overall_match_status).className
                    }`}
                  >
                    {getStatusBadge(selectedProgram.overall_match_status).labelAr}
                  </span>
                </div>
                <h3 className="text-lg font-bold text-foreground mt-1">
                  {selectedProgram.program_name_ar}
                </h3>
                <p className="text-xs text-muted-foreground">{selectedProgram.program_name_en}</p>
              </div>
              <button
                onClick={() => setSelectedProgram(null)}
                className="text-muted-foreground hover:text-foreground text-xl font-bold p-1"
                aria-label="إغلاق"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4 overflow-y-auto">
              <div className="p-3 rounded-lg bg-muted/40 border border-border/60 text-xs space-y-1">
                <div className="font-semibold text-foreground">نتيجة المطابقة:</div>
                <p>{selectedProgram.status_reason_ar}</p>
                <p className="text-muted-foreground text-[11px]">{selectedProgram.status_reason_en}</p>
              </div>

              <div>
                <h4 className="font-bold text-sm text-foreground mb-3">
                  سجل فحص القواعد بالتفصيل (Rule-by-Rule Provenance)
                </h4>

                <div className="space-y-3">
                  {selectedProgram.rule_evaluations.map((ev: FundingRuleEvaluation) => {
                    const rBadge = getRuleResultBadge(ev.result);
                    return (
                      <div
                        key={ev.rule_key}
                        className="p-3 rounded-lg border border-border bg-background space-y-2 text-xs"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="font-bold text-foreground text-sm">
                              {ev.rule_name_ar}
                            </span>
                            <span className="text-muted-foreground text-[11px] block">
                              {ev.rule_name_en} • ({ev.rule_type})
                            </span>
                          </div>
                          <span
                            className={`px-2 py-0.5 rounded border text-[11px] font-semibold whitespace-nowrap ${rBadge.className}`}
                          >
                            {rBadge.label}
                          </span>
                        </div>

                        {/* Values grid */}
                        <div className="grid grid-cols-2 gap-2 p-2 rounded bg-muted/30 border border-border/30">
                          <div>
                            <span className="text-muted-foreground block text-[10px]">القيد المطلوب (Required)</span>
                            <span className="font-mono text-foreground font-medium break-all">
                              {typeof ev.required_value === "object"
                                ? JSON.stringify(ev.required_value)
                                : String(ev.required_value)}
                            </span>
                          </div>
                          <div>
                            <span className="text-muted-foreground block text-[10px]">بيانات الدراسة (Actual)</span>
                            <span className="font-mono text-foreground font-medium break-all">
                              {typeof ev.actual_value === "object"
                                ? JSON.stringify(ev.actual_value)
                                : String(ev.actual_value)}
                            </span>
                          </div>
                        </div>

                        {/* Notes */}
                        <div className="text-[11px] text-foreground">
                          <p>{ev.notes_ar}</p>
                          <p className="text-muted-foreground">{ev.notes_en}</p>
                        </div>

                        {/* Provenance Footer */}
                        <div className="pt-2 border-t border-border/40 flex flex-wrap items-center justify-between gap-2 text-[10px] text-muted-foreground">
                          <span>الجهة المصدرة: {ev.source_authority} • v{ev.rule_version}</span>
                          {ev.source_url && (
                            <a
                              href={ev.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-primary hover:underline flex items-center gap-0.5"
                            >
                              المصدر الرسمي المعتمد ↗
                            </a>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-border flex items-center justify-between">
              <a
                href={selectedProgram.official_source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary hover:underline"
              >
                زيارة صفحة البرنامج الرسمية لدى {selectedProgram.provider} ↗
              </a>
              <button
                onClick={() => setSelectedProgram(null)}
                className="px-4 py-1.5 text-xs font-medium rounded-lg border border-border bg-background hover:bg-muted transition"
              >
                إغلاق
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
