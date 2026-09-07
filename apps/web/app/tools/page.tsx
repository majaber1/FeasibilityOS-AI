"use client";

import { useLanguage } from "@/components/LanguageProvider";
import { ServiceCard } from "@/components/ui/ServiceCard";

const services = [
  {
    href: "/tools/feasibility",
    icon: "📊",
    code: "01",
    title: { ar: "دراسة الجدوى V2", en: "Feasibility Study V2" },
    description: {
      ar: "محرك ذكاء اصطناعي متعدد الوكلاء يحلل مشروعك ويعطيك قرارًا استثماريًا واضحًا.",
      en: "A multi-agent AI engine that analyzes your project and delivers a clear investment decision.",
    },
  },
  {
    href: "/tools/financial",
    icon: "💰",
    code: "02",
    title: { ar: "التحليل المالي", en: "Financial Analysis" },
    description: {
      ar: "حلل العائد والقيمة الحالية ومعدل العائد الداخلي وفترة الاسترداد ونقطة التعادل بشكل مستقل.",
      en: "Analyze ROI, NPV, IRR, payback period, and break-even independently for any scenario.",
    },
  },
  {
    href: "/tools/funding",
    icon: "🏦",
    code: "03",
    title: { ar: "مطابقة التمويل", en: "Funding Matcher" },
    description: {
      ar: "مطابقة شفّافة مع برامج التمويل السعودية حسب قطاعك ومرحلتك وجاهزيتك.",
      en: "Transparent matching with Saudi funding programs based on your sector, stage, and readiness.",
    },
  },
  {
    href: "/tools/opportunities",
    icon: "🎯",
    code: "04",
    title: { ar: "رادار الفرص", en: "Opportunity Radar" },
    description: {
      ar: "تصفّح فرصًا مصنّفة حسب القطاع والمخاطر وحجم الاستثمار.",
      en: "Browse opportunities categorized by sector, risk level, and investment size.",
    },
  },
  {
    href: "/tools/ideas",
    icon: "💡",
    code: "05",
    title: { ar: "بنك الأفكار", en: "Idea Bank" },
    description: {
      ar: "أفكار مشاريع متوافقة مع رؤية 2030 ومصنفة حسب القطاع ومستوى الصعوبة.",
      en: "Vision 2030-aligned project ideas categorized by sector and difficulty level.",
    },
  },
  {
    href: "/tools/proposal",
    icon: "📝",
    code: "06",
    title: { ar: "منشئ العروض", en: "Proposal Builder" },
    description: {
      ar: "أنشئ عروضًا تجارية احترافية باللغتين وصدّرها PDF أو Word.",
      en: "Build professional business proposals in Arabic and English, export to PDF or Word.",
    },
    comingSoon: true,
  },
  {
    href: "/tools/qualification",
    icon: "✅",
    code: "07",
    title: { ar: "تأهيل الأعمال", en: "Business Qualification" },
    description: {
      ar: "اعرف مدى جاهزية منشأتك للتمويل والمناقصات والامتثال.",
      en: "Assess your business readiness for funding, tenders, and compliance.",
    },
    comingSoon: true,
  },
  {
    href: "/tools/franchise",
    icon: "🏪",
    code: "08",
    title: { ar: "الامتياز التجاري", en: "Franchise" },
    description: {
      ar: "استعرض فرص الامتياز التجاري المتاحة في السوق السعودي.",
      en: "Explore franchise opportunities available in the Saudi market.",
    },
    comingSoon: true,
  },
  {
    href: "/tools/auctions",
    icon: "🔨",
    code: "09",
    title: { ar: "المزادات", en: "Auctions" },
    description: {
      ar: "تصفّح مزادات الأعمال والأصول التجارية.",
      en: "Browse business and commercial asset auctions.",
    },
    comingSoon: true,
  },
  {
    href: "/tools/reports",
    icon: "📄",
    code: "10",
    title: { ar: "التقارير وحزمة المستثمر", en: "Reports & Investor Package" },
    description: {
      ar: "أنشئ تقارير احترافية وحزمة المستثمر من دراساتك وتحليلاتك.",
      en: "Generate professional reports and investor packages from your studies and analyses.",
    },
    comingSoon: true,
  },
];

export default function ToolsPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";

  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <section className="border-b border-slate-200 bg-white">
        <div className="container-page py-12">
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-brand-600">
            {ar ? "أدوات سعودي بزنس" : "Saudi Business Tools"}
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">
            {ar ? "كل ما تحتاجه من الفكرة إلى الاستثمار" : "Everything from idea to investment"}
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-ink-600">
            {ar
              ? "كل خدمة مستقلة ويمكن استخدامها بشكل منفصل أو ربطها بمشروعك."
              : "Each service is independent — use it standalone or link it to your business."}
          </p>
        </div>
      </section>

      <div className="container-page py-10">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {services.map((s) => (
            <div key={s.href} className="relative">
              {"comingSoon" in s && s.comingSoon && (
                <span className="absolute end-3 top-3 z-10 rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-bold text-amber-800">
                  {ar ? "قريبًا" : "Coming soon"}
                </span>
              )}
              <div className={"comingSoon" in s && s.comingSoon ? "pointer-events-none opacity-60" : ""}>
                <ServiceCard
                  href={s.href}
                  icon={s.icon}
                  code={s.code}
                  title={ar ? s.title.ar : s.title.en}
                  description={ar ? s.description.ar : s.description.en}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
