"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { ServiceHeader } from "@/components/ui/ServiceHeader";
import { KpiCard } from "@/components/ui/KpiCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Badge } from "@/components/ui/Badge";
import { getToken, listQualificationProfiles, type QualificationProfile } from "@/lib/api";
import { useProjectContext } from "@/lib/use-project-context";

const categories = [
  { key: "legal", icon: "⚖️", ar: "الجاهزية القانونية", en: "Legal readiness" },
  { key: "operational", icon: "⚙️", ar: "الجاهزية التشغيلية", en: "Operational readiness" },
  { key: "digital", icon: "💻", ar: "الجاهزية الرقمية", en: "Digital readiness" },
  { key: "financial", icon: "💰", ar: "الجاهزية المالية", en: "Financial readiness" },
  { key: "compliance", icon: "📋", ar: "جاهزية الامتثال", en: "Compliance readiness" },
  { key: "market", icon: "📈", ar: "جاهزية السوق", en: "Market readiness" },
];

export default function QualificationServicePage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const [profiles, setProfiles] = useState<QualificationProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [signedIn, setSignedIn] = useState(false);
  const { project } = useProjectContext();
  const assessmentHref = project ? `/qualification?project_id=${project.id}` : "/qualification";

  useEffect(() => {
    const token = getToken();
    if (!token) { setLoading(false); return; }
    setSignedIn(true);
    listQualificationProfiles(token)
      .then(setProfiles)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const latestProfile = profiles[0];

  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <ServiceHeader
        icon="✅"
        title={ar ? "تأهيل الأعمال" : "Business Qualification"}
        subtitle={ar ? "اعرف مدى جاهزية منشأتك للتمويل والمناقصات والنمو" : "Assess your business readiness for funding, tenders, and growth"}
        breadcrumb={[{ label: ar ? "الأدوات" : "Tools", href: "/tools" }]}
        actions={
          signedIn ? (
            <Link href={assessmentHref} className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-brand-700">
              {latestProfile ? (ar ? "تحديث التقييم" : "Update assessment") : (ar ? "بدء التقييم" : "Start assessment")}
            </Link>
          ) : undefined
        }
      />

      <div className="container-page space-y-8 py-8">
        <section className="rounded-2xl border border-brand-200 bg-white p-6 shadow-card sm:p-8">
          <h2 className="text-xl font-bold text-ink-900">{ar ? "ما الذي نقيّمه" : "What we assess"}</h2>
          <p className="mt-2 text-sm text-ink-600">{ar ? "التقييم يغطي ست مجالات رئيسية لجاهزية أعمالك:" : "The assessment covers six key areas of business readiness:"}</p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {categories.map((c) => (
              <div key={c.key} className="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4">
                <span className="mt-0.5 text-xl">{c.icon}</span>
                <div>
                  <p className="font-semibold text-ink-800">{ar ? c.ar : c.en}</p>
                  {latestProfile?.category_scores?.[c.key] !== undefined && (
                    <p className="mt-1 text-sm text-brand-600">{Math.round(latestProfile.category_scores[c.key])}%</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        {signedIn && latestProfile && (
          <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label={ar ? "الدرجة الإجمالية" : "Overall score"} value={`${Math.round(latestProfile.overall_score)}%`} icon="📊" />
            <KpiCard label={ar ? "المتطلبات" : "Requirements"} value={String(latestProfile.recommendations?.length || 0)} icon="📋" />
            <KpiCard label={ar ? "القطاع" : "Sector"} value={latestProfile.sector || "—"} icon="🏭" />
            <KpiCard label={ar ? "حجم المنشأة" : "Company size"} value={latestProfile.company_size || "—"} icon="🏢" />
          </section>
        )}

        {!signedIn ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-card">
            <h2 className="text-xl font-bold text-ink-900">{ar ? "سجّل الدخول لبدء التقييم" : "Sign in to start your assessment"}</h2>
            <p className="mt-2 text-sm text-ink-600">{ar ? "التقييم مجاني ويمكنك تحديثه في أي وقت." : "The assessment is free and can be updated anytime."}</p>
            <Link href="/login" className="mt-6 inline-flex rounded-xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white">{ar ? "تسجيل الدخول" : "Sign in"}</Link>
          </div>
        ) : loading ? (
          <div className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white" />
        ) : !latestProfile ? (
          <EmptyState
            icon="✅"
            title={ar ? "لم يتم التقييم بعد" : "No assessment yet"}
            description={ar ? "ابدأ بتقييم جاهزية أعمالك لتحديد نقاط القوة والتحسين." : "Start assessing your business readiness to identify strengths and areas for improvement."}
            actionLabel={ar ? "بدء التقييم" : "Start assessment"}
            actionHref={assessmentHref}
          />
        ) : (
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-ink-900">{ar ? "التوصيات" : "Recommendations"}</h2>
              <Badge variant="brand">{ar ? "آخر تقييم" : "Latest"}</Badge>
            </div>
            {latestProfile.recommendations && latestProfile.recommendations.length > 0 ? (
              <ul className="mt-4 space-y-3">
                {latestProfile.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50 p-4">
                    <span className="mt-0.5 text-brand-600">→</span>
                    <p className="text-sm text-ink-700">{typeof rec === "string" ? rec : JSON.stringify(rec)}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-4 text-sm text-ink-500">{ar ? "لا توجد توصيات حالية." : "No current recommendations."}</p>
            )}
          </section>
        )}

        <section className="rounded-xl border border-blue-200 bg-blue-50 p-5">
          <h3 className="font-semibold text-blue-800">{ar ? "الامتثال المتقدم" : "Advanced compliance"}</h3>
          <p className="mt-2 text-sm text-blue-700">
            {ar
              ? "للمتطلبات التنظيمية المتقدمة (GRC، ضوابط NCA، PDPL)، يمكنك طلب تقييم من ملتزم."
              : "For advanced regulatory requirements (GRC, NCA controls, PDPL), you can request an assessment from Multazim."}
          </p>
          <Link href="/multazim" className="mt-2 inline-flex text-sm font-bold text-blue-700 hover:text-blue-800">{ar ? "معرفة المزيد" : "Learn more"}</Link>
        </section>
      </div>
    </div>
  );
}
