"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { ServiceHeader } from "@/components/ui/ServiceHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { getToken, listStudies, reportDownloadUrl, type Study } from "@/lib/api";
import { useProjectContext } from "@/lib/use-project-context";

const reportTypes = [
  { key: "feasibility", icon: "📊", ar: "تقرير دراسة الجدوى", en: "Feasibility Report" },
];

export default function ReportsServicePage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const [studies, setStudies] = useState<Study[]>([]);
  const [loading, setLoading] = useState(true);
  const [signedIn, setSignedIn] = useState(false);
  const [error, setError] = useState("");
  const { project, error: projectError } = useProjectContext();

  useEffect(() => {
    const token = getToken();
    if (!token) { setLoading(false); return; }
    setSignedIn(true);
    listStudies(token, project?.id)
      .then(setStudies)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, [project?.id]);

  async function downloadReport(studyId: number, format: "pdf" | "docx", language: "ar" | "en") {
    const token = getToken();
    if (!token) return;
    setError("");
    try {
      const response = await fetch(reportDownloadUrl(studyId, format, language), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || response.statusText);
      }
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `feasibility_${studyId}_${language}.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const completed = studies.filter((s) => s.status === "completed");

  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <ServiceHeader
        icon="📄"
        title={ar ? "التقارير وحزمة المستثمر" : "Reports & Investor Package"}
        subtitle={ar ? "أنشئ تقارير احترافية من دراساتك وتحليلاتك" : "Generate professional reports from your studies and analyses"}
        breadcrumb={[{ label: ar ? "الأدوات" : "Tools", href: "/tools" }]}
      />

      <div className="container-page space-y-8 py-8">
        {project && <div className="rounded-xl border border-brand-200 bg-brand-50 px-5 py-4 text-sm text-brand-800">{ar ? "تقارير المشروع:" : "Project reports:"} <strong>{project.name}</strong></div>}
        {(error || projectError) && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error || projectError}</p>}
        <section className="rounded-2xl border border-brand-200 bg-white p-6 shadow-card sm:p-8">
          <h2 className="text-xl font-bold text-ink-900">{ar ? "أنواع التقارير" : "Report types"}</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {reportTypes.map((rt) => (
              <div key={rt.key} className="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50 p-5">
                <span className="mt-0.5 text-2xl">{rt.icon}</span>
                <p className="font-semibold text-ink-800">{ar ? rt.ar : rt.en}</p>
              </div>
            ))}
          </div>
        </section>

        {!signedIn ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-card">
            <h2 className="text-xl font-bold text-ink-900">{ar ? "سجّل الدخول لتنزيل التقارير" : "Sign in to download reports"}</h2>
            <p className="mt-2 text-sm text-ink-600">{ar ? "أكمل دراسة جدوى أولاً ثم قم بتصدير التقرير." : "Complete a feasibility study first, then export the report."}</p>
            <Link href="/login" className="mt-6 inline-flex rounded-xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white">{ar ? "تسجيل الدخول" : "Sign in"}</Link>
          </div>
        ) : loading ? (
          <div className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white" />
        ) : completed.length === 0 ? (
          <EmptyState
            icon="📄"
            title={ar ? "لا توجد تقارير جاهزة" : "No reports ready"}
            description={ar ? "أكمل دراسة جدوى لتتمكن من تصدير التقرير." : "Complete a feasibility study to export a report."}
            actionLabel={ar ? "بدء دراسة" : "Start a study"}
            actionHref="/feasibility/new"
          />
        ) : (
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
            <header className="border-b border-slate-100 px-6 py-4">
              <h2 className="font-bold text-ink-900">{ar ? "الدراسات الجاهزة للتصدير" : "Studies ready for export"}</h2>
            </header>
            <div className="divide-y divide-slate-100">
              {completed.map((s) => (
                <div key={s.id} className="flex flex-wrap items-center justify-between gap-4 px-6 py-4 transition hover:bg-slate-50">
                  <div>
                    <p className="font-semibold text-ink-900">{s.title}</p>
                    <p className="mt-1 text-xs text-ink-500">{s.study_type}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => downloadReport(s.id, "pdf", "ar")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-bold text-ink-700 hover:border-brand-500 hover:text-brand-600">
                      PDF {ar ? "عربي" : "AR"}
                    </button>
                    <button onClick={() => downloadReport(s.id, "pdf", "en")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-bold text-ink-700 hover:border-brand-500 hover:text-brand-600">
                      PDF {ar ? "إنجليزي" : "EN"}
                    </button>
                    <button onClick={() => downloadReport(s.id, "docx", "ar")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-bold text-ink-700 hover:border-brand-500 hover:text-brand-600">
                      DOCX {ar ? "عربي" : "AR"}
                    </button>
                    <button onClick={() => downloadReport(s.id, "docx", "en")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-bold text-ink-700 hover:border-brand-500 hover:text-brand-600">
                      DOCX {ar ? "إنجليزي" : "EN"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
