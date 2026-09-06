"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { ServiceHeader } from "@/components/ui/ServiceHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import { getToken, listStudies, type Study } from "@/lib/api";

export default function FeasibilityServicePage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const [studies, setStudies] = useState<Study[]>([]);
  const [loading, setLoading] = useState(true);
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) { setLoading(false); return; }
    setSignedIn(true);
    listStudies(token)
      .then(setStudies)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const completed = studies.filter((s) => s.status === "completed");
  const drafts = studies.filter((s) => s.status === "draft");
  const feasible = completed.filter((s) => s.result?.verdict === "feasible");

  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <ServiceHeader
        icon="📊"
        title={ar ? "دراسة الجدوى" : "Feasibility Study"}
        subtitle={ar
          ? "محرّك مالي حقيقي يحلل جدوى مشروعك ويعطيك قرارًا واضحًا"
          : "A real financial engine that analyzes your project's viability and gives you a clear decision"}
        breadcrumb={[{ label: ar ? "الأدوات" : "Tools", href: "/tools" }]}
        actions={
          <Link
            href="/projects"
            className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-brand-700"
          >
            {ar ? "دراسة جديدة" : "New study"}
          </Link>
        }
      />

      <div className="container-page space-y-8 py-8">
        {signedIn && !loading && (
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label={ar ? "إجمالي الدراسات" : "Total studies"} value={String(studies.length)} icon="📊" />
            <KpiCard label={ar ? "مكتملة" : "Completed"} value={String(completed.length)} icon="✅" />
            <KpiCard label={ar ? "مجدية" : "Feasible"} value={String(feasible.length)} icon="🎯" />
            <KpiCard label={ar ? "مسودات" : "Drafts"} value={String(drafts.length)} icon="📝" />
          </section>
        )}

        <section className="rounded-2xl border border-brand-200 bg-white p-6 shadow-card sm:p-8">
          <h2 className="text-xl font-bold text-ink-900">{ar ? "كيف تعمل الدراسة" : "How it works"}</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { step: "1", title: ar ? "بيانات المشروع" : "Project details", desc: ar ? "الاسم والقطاع والاستثمار المتوقع" : "Name, sector, and expected investment" },
              { step: "2", title: ar ? "الافتراضات المالية" : "Financial assumptions", desc: ar ? "الإيرادات والتكاليف ومعدل النمو" : "Revenue, costs, and growth rate" },
              { step: "3", title: ar ? "التحليل والنتائج" : "Analysis & results", desc: ar ? "NPV و IRR و ROI وتحليل الحساسية" : "NPV, IRR, ROI, and sensitivity analysis" },
              { step: "4", title: ar ? "التقرير" : "Report", desc: ar ? "تقرير احترافي PDF أو Word" : "Professional PDF or Word report" },
            ].map((s) => (
              <div key={s.step} className="rounded-xl border border-slate-100 bg-slate-50 p-5">
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-100 text-sm font-bold text-brand-700">{s.step}</span>
                <h3 className="mt-3 font-bold text-ink-900">{s.title}</h3>
                <p className="mt-1 text-sm text-ink-600">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {!signedIn ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-card">
            <h2 className="text-xl font-bold text-ink-900">{ar ? "سجّل الدخول لعرض دراساتك" : "Sign in to see your studies"}</h2>
            <p className="mt-2 text-sm text-ink-600">{ar ? "أو ابدأ دراسة جديدة بدون حساب." : "Or start a new study without an account."}</p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <Link href="/login" className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-ink-700 hover:border-brand-500">{ar ? "تسجيل الدخول" : "Sign in"}</Link>
              <Link href="/feasibility/new" className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-700">{ar ? "ابدأ دراسة جديدة" : "Start a new study"}</Link>
            </div>
          </div>
        ) : loading ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {[0, 1].map((i) => <div key={i} className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white" />)}
          </div>
        ) : studies.length === 0 ? (
          <EmptyState
            icon="📊"
            title={ar ? "لا توجد دراسات بعد" : "No studies yet"}
            description={ar ? "ابدأ أول دراسة جدوى لمشروعك." : "Start your first feasibility study."}
            actionLabel={ar ? "دراسة جديدة" : "New study"}
            actionHref="/projects"
          />
        ) : (
          <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
            <header className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
              <h2 className="font-bold text-ink-900">{ar ? "دراساتك" : "Your studies"}</h2>
            </header>
            <div className="divide-y divide-slate-100">
              {studies.map((s) => (
                <Link
                  key={s.id}
                  href={`/projects/${s.project_id}/studies/${s.id}`}
                  data-testid={`open-study-${s.id}`}
                  className="flex items-center justify-between px-6 py-4 transition hover:bg-slate-50"
                >
                  <div>
                    <p className="font-semibold text-ink-900">{s.title}</p>
                    <p className="mt-1 text-xs text-ink-500">{s.study_type} — {ar ? `خطوة ${s.current_step}` : `Step ${s.current_step}`}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    {s.result ? (
                      <Badge variant={s.result.verdict === "feasible" ? "success" : s.result.verdict === "not_feasible" ? "danger" : "warning"}>
                        {s.result.verdict === "feasible" ? (ar ? "مجدٍ" : "Feasible") : s.result.verdict === "not_feasible" ? (ar ? "غير مجدٍ" : "Not Feasible") : (ar ? "حدّي" : "Borderline")}
                      </Badge>
                    ) : (
                      <Badge variant="neutral">{ar ? "مسودة" : "Draft"}</Badge>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
