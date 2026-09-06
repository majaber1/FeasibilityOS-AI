"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import { ServiceHeader } from "@/components/ui/ServiceHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { getToken, getProject, listStudies, type Project, type Study } from "@/lib/api";

function money(value: number, locale: "ar" | "en") {
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-SA", {
    style: "currency",
    currency: "SAR",
    maximumFractionDigits: 0,
  }).format(value);
}

const toolLinks = (id: string, ar: boolean) => [
  { href: `/projects/${id}`, icon: "📊", label: ar ? "دراسة الجدوى" : "Feasibility Study" },
  { href: `/tools/financial?business=${id}`, icon: "💰", label: ar ? "التحليل المالي" : "Financial Analysis" },
  { href: `/tools/proposal?business=${id}`, icon: "📝", label: ar ? "منشئ العروض" : "Proposal Builder" },
  { href: `/tools/funding?business=${id}`, icon: "🏦", label: ar ? "مطابقة التمويل" : "Funding Matcher" },
  { href: `/tools/qualification?business=${id}`, icon: "✅", label: ar ? "تأهيل الأعمال" : "Qualification" },
  { href: `/tools/reports?business=${id}`, icon: "📄", label: ar ? "التقارير" : "Reports" },
];

export default function BusinessDetailPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const params = useParams();
  const id = params.id as string;
  const [project, setProject] = useState<Project | null>(null);
  const [studies, setStudies] = useState<Study[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) { setLoading(false); return; }

    Promise.all([
      getProject(token, Number(id)),
      listStudies(token, Number(id)).catch(() => []),
    ])
      .then(([p, s]) => {
        setProject(p);
        setStudies(s);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f7f6]">
        <div className="container-page py-20 text-center">
          <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-[#f5f7f6]">
        <div className="container-page py-20 text-center">
          <p className="text-lg text-ink-600">{ar ? "المشروع غير موجود" : "Project not found"}</p>
          <Link href="/businesses" className="mt-4 inline-flex text-sm font-bold text-brand-600">{ar ? "العودة" : "Go back"}</Link>
        </div>
      </div>
    );
  }

  const completedStudies = studies.filter((s) => s.status === "completed");

  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <ServiceHeader
        icon="🏢"
        title={project.name}
        subtitle={project.industry}
        breadcrumb={[{ label: ar ? "أعمالي" : "My Businesses", href: "/businesses" }]}
        actions={
          <div className="flex flex-wrap gap-2">
            <Link
              href={`/projects/${id}`}
              data-testid="open-project-workspace"
              className="rounded-xl border border-brand-200 bg-white px-5 py-3 text-sm font-semibold text-brand-700 shadow-card hover:bg-brand-50"
            >
              {ar ? "ملف المشروع" : "Project file"}
            </Link>
            <Link
              href={studies[0] ? `/projects/${id}/studies/${studies[0].id}` : `/projects/${id}`}
              data-testid="open-or-start-study"
              className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-brand-700"
            >
              {studies[0] ? (ar ? "متابعة الدراسة الحالية" : "Continue existing study") : (ar ? "ابدأ الدراسة" : "Start study")}
            </Link>
          </div>
        }
      />

      <div className="container-page space-y-8 py-8">
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard label={ar ? "الاستثمار" : "Investment"} value={money(Number(project.investment), locale as "ar" | "en")} icon="💰" />
          <KpiCard label={ar ? "المرحلة" : "Stage"} value={project.stage || "—"} icon="📈" />
          <KpiCard label={ar ? "دراسات الجدوى" : "Studies"} value={String(studies.length)} hint={`${completedStudies.length} ${ar ? "مكتملة" : "completed"}`} icon="📊" />
          <KpiCard label={ar ? "تاريخ الإنشاء" : "Created"} value={new Date(project.created_at).toLocaleDateString(ar ? "ar-SA" : "en-SA")} icon="📅" />
        </section>

        <section>
          <h2 className="mb-4 text-lg font-bold text-ink-900">{ar ? "الأدوات المتاحة" : "Available Tools"}</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {toolLinks(id, ar).map((tool) => (
              <Link key={tool.href} href={tool.href}>
                <div className="group flex items-center gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-card-hover">
                  <span className="text-2xl">{tool.icon}</span>
                  <div>
                    <p className="font-semibold text-ink-900 group-hover:text-brand-700">{tool.label}</p>
                  </div>
                  <span className="ms-auto text-brand-600 transition group-hover:translate-x-0.5 rtl:group-hover:-translate-x-0.5">→</span>
                </div>
              </Link>
            ))}
          </div>
        </section>

        {studies.length > 0 && (
          <section>
            <h2 className="mb-4 text-lg font-bold text-ink-900">{ar ? "الدراسات" : "Studies"}</h2>
            <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-card">
              <div className="divide-y divide-slate-100">
                {studies.map((s) => (
                  <Link
                    key={s.id}
                    href={`/projects/${id}/studies/${s.id}`}
                    data-testid={`open-study-${s.id}`}
                    className="flex items-center justify-between px-6 py-4 transition hover:bg-slate-50"
                  >
                    <div>
                      <p className="font-semibold text-ink-900">{s.title}</p>
                      <p className="mt-1 text-xs text-ink-500">{s.study_type} — {s.status}</p>
                    </div>
                    {s.result && (
                      <span className={`rounded-full px-3 py-1 text-xs font-bold ${s.result.verdict === "feasible" ? "bg-emerald-50 text-emerald-700" : s.result.verdict === "not_feasible" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>
                        {s.result.verdict === "feasible" ? (ar ? "مجدٍ" : "Feasible") : s.result.verdict === "not_feasible" ? (ar ? "غير مجدٍ" : "Not Feasible") : (ar ? "حدّي" : "Borderline")}
                      </span>
                    )}
                  </Link>
                ))}
              </div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
