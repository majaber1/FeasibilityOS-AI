"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";

const services = [
  { href: "/tools/feasibility", icon: "▦", code: "01", title: { ar: "دراسة الجدوى", en: "Feasibility Study" }, desc: { ar: "ابنِ دراسة قابلة للمراجعة مع افتراضات ونتائج مالية واضحة.", en: "Build a reviewable study with explicit assumptions and financial outputs." }, tag: { ar: "ابدأ من هنا", en: "Start here" } },
  { href: "/tools/financial", icon: "↗", code: "02", title: { ar: "التحليل المالي", en: "Financial Analysis" }, desc: { ar: "ROI وNPV وIRR وتحليل الحساسية في مساحة قرار واحدة.", en: "ROI, NPV, IRR and sensitivity analysis in one decision workspace." }, tag: { ar: "قرار مالي", en: "Financial decision" } },
  { href: "/tools/funding", icon: "﷼", code: "03", title: { ar: "مطابقة التمويل", en: "Funding Matcher" }, desc: { ar: "اعرف البرامج الأقرب لحالتك ولماذا، قبل تجهيز ملف التقديم.", en: "See which programs fit your case and why before preparing the application." }, tag: { ar: "تمويل سعودي", en: "Saudi funding" } },
  { href: "/tools/qualification", icon: "✓", code: "04", title: { ar: "تأهيل الأعمال", en: "Qualification" }, desc: { ar: "قياس جاهزية المنشأة للتمويل والاستثمار والمناقصات.", en: "Measure business readiness for funding, investment and tenders." }, tag: { ar: "جاهزية", en: "Readiness" } },
  { href: "/tools/proposal", icon: "✦", code: "05", title: { ar: "منشئ العروض", en: "Proposal Builder" }, desc: { ar: "حوّل بيانات المشروع إلى عرض واضح للممول أو المستثمر.", en: "Turn project data into a clear proposal for funders or investors." }, tag: { ar: "حزمة المستثمر", en: "Investor package" } },
  { href: "/tools/opportunities", icon: "◎", code: "06", title: { ar: "فرص الاستثمار", en: "Opportunities" }, desc: { ar: "استكشف الفرص حسب القطاع والمخاطر والملاءمة التجارية.", en: "Explore opportunities by sector, risk and commercial fit." }, tag: { ar: "فرص", en: "Opportunities" } },
];

const journey = [
  { step: "01", ar: "عرّف مشروعك", en: "Define the business" },
  { step: "02", ar: "اختبر الجدوى", en: "Test feasibility" },
  { step: "03", ar: "قيّم الجاهزية", en: "Assess readiness" },
  { step: "04", ar: "طابق التمويل", en: "Match funding" },
  { step: "05", ar: "جهّز العرض", en: "Prepare the pitch" },
];

const stats = [
  { ar: "6 أدوات مترابطة", en: "6 connected tools" },
  { ar: "عربي + English", en: "Arabic + English" },
  { ar: "سياق سعودي", en: "Saudi-first context" },
];

export default function HomePage() {
  const { t, locale } = useLanguage();
  const ar = locale === "ar";

  return (
    <div className="overflow-hidden bg-[#f7f8f5]">
      <section className="relative isolate overflow-hidden border-b border-white/10 bg-[#062c1d] text-white">
        <div className="absolute inset-0 -z-10 opacity-80 [background:radial-gradient(circle_at_15%_10%,rgba(201,162,39,.23),transparent_34%),radial-gradient(circle_at_85%_35%,rgba(31,157,92,.22),transparent_38%),linear-gradient(135deg,#062c1d_0%,#084a2a_55%,#052719_100%)]" />
        <div className="absolute inset-0 -z-10 opacity-[0.08] [background-image:linear-gradient(rgba(255,255,255,.5)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.5)_1px,transparent_1px)] [background-size:48px_48px]" />

        <div className="container-page grid items-center gap-12 py-20 lg:grid-cols-[1.15fr_.85fr] lg:py-28">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1.5 text-xs font-bold text-white/90 backdrop-blur">
              <span className="h-2 w-2 rounded-full bg-gold-400" />
              {t.tagline}
            </div>
            <h1 className="mt-6 max-w-4xl text-4xl font-extrabold leading-[1.12] tracking-tight sm:text-5xl lg:text-6xl">
              {ar ? "حوّل فكرة المشروع إلى قرار استثماري قابل للدفاع عنه" : "Turn a business idea into a defensible investment decision"}
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-8 text-white/72 sm:text-lg">
              {ar
                ? "سعودي بزنس يجمع دراسة الجدوى، التحليل المالي، التأهيل، مطابقة التمويل وحزمة المستثمر في رحلة واحدة — مع إبقاء كل أداة مستقلة عندما تحتاجها وحدها."
                : "Saudi Business connects feasibility, financial analysis, qualification, funding matching and investor packaging in one journey — while keeping every tool independently usable."}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/tools/feasibility" className="rounded-xl bg-gold-400 px-6 py-3.5 text-sm font-extrabold text-[#062c1d] shadow-[0_16px_40px_rgba(0,0,0,.18)] transition hover:-translate-y-0.5 hover:bg-gold-300">
                {ar ? "ابدأ مشروعك الآن" : "Start your business case"}
              </Link>
              <Link href="/tools" className="rounded-xl border border-white/20 bg-white/10 px-6 py-3.5 text-sm font-bold text-white backdrop-blur transition hover:bg-white/15">
                {ar ? "استعرض كل الأدوات" : "Explore all tools"}
              </Link>
            </div>
            <div className="mt-10 flex flex-wrap gap-x-7 gap-y-3 border-t border-white/10 pt-6 text-xs font-semibold text-white/65">
              {stats.map((s) => <span key={s.en}>✓ {ar ? s.ar : s.en}</span>)}
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-xl lg:mx-0">
            <div className="absolute -inset-6 -z-10 rounded-[2rem] bg-gold-400/10 blur-3xl" />
            <div className="rounded-[1.75rem] border border-white/15 bg-white/[0.08] p-4 shadow-2xl backdrop-blur-xl sm:p-6">
              <div className="flex items-center justify-between border-b border-white/10 pb-5">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-gold-300">{ar ? "لوحة القرار" : "Decision cockpit"}</p>
                  <h2 className="mt-2 text-xl font-bold">{ar ? "جاهزية مشروعك" : "Business readiness"}</h2>
                </div>
                <div className="grid h-14 w-14 place-items-center rounded-2xl border border-gold-300/20 bg-gold-300/10 text-xl font-black text-gold-300">78</div>
              </div>
              <div className="mt-5 space-y-3">
                {[
                  [ar ? "الجدوى المالية" : "Financial viability", "84%"],
                  [ar ? "جاهزية التمويل" : "Funding readiness", "72%"],
                  [ar ? "اكتمال البيانات" : "Data completeness", "91%"],
                ].map(([label, value]) => (
                  <div key={label} className="rounded-2xl border border-white/10 bg-black/10 p-4">
                    <div className="flex items-center justify-between text-sm"><span className="text-white/75">{label}</span><strong>{value}</strong></div>
                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-gradient-to-r from-gold-400 to-emerald-400" style={{ width: value }} /></div>
                  </div>
                ))}
              </div>
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-4"><small className="text-white/55">{ar ? "أفضل خطوة تالية" : "Best next step"}</small><strong className="mt-1 block text-sm">{ar ? "مطابقة التمويل" : "Funding match"}</strong></div>
                <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-4"><small className="text-white/55">{ar ? "حالة الملف" : "Case status"}</small><strong className="mt-1 block text-sm text-emerald-300">{ar ? "قابل للتطوير" : "Actionable"}</strong></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-slate-200/80 bg-white">
        <div className="container-page py-8">
          <div className="grid gap-2 sm:grid-cols-5">
            {journey.map((j) => (
              <div key={j.step} className="group rounded-2xl border border-transparent p-4 transition hover:border-brand-100 hover:bg-brand-50/60">
                <span className="text-[11px] font-black tracking-[.16em] text-brand-600">{j.step}</span>
                <p className="mt-1 text-sm font-bold text-ink-900">{ar ? j.ar : j.en}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="container-page py-16 sm:py-20">
        <div className="flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-black uppercase tracking-[.18em] text-brand-600">{ar ? "مساحة العمل" : "Business workspace"}</p>
            <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-ink-900">{ar ? "كل قرار تجاري في مكانه الصحيح" : "Every business decision in the right workspace"}</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-ink-600">{ar ? "استخدم أداة واحدة أو اربط الأدوات بسياق مشروعك لتنتقل من الفكرة إلى ملف جاهز للتمويل والاستثمار." : "Use one tool on its own, or connect them through your business context to move from idea to funding and investment readiness."}</p>
          </div>
          <Link href="/tools" className="text-sm font-extrabold text-brand-700 hover:text-brand-800">{ar ? "عرض مركز الأدوات ←" : "Open tool center →"}</Link>
        </div>

        <div className="mt-9 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {services.map((s) => (
            <Link key={s.href} href={s.href} className="group relative overflow-hidden rounded-[1.4rem] border border-slate-200 bg-white p-6 shadow-[0_8px_30px_rgba(15,23,42,.04)] transition duration-300 hover:-translate-y-1 hover:border-brand-200 hover:shadow-[0_20px_50px_rgba(8,74,42,.11)]">
              <div className="absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r from-transparent via-brand-500 to-transparent opacity-0 transition group-hover:opacity-100" />
              <div className="flex items-start justify-between gap-4">
                <span className="grid h-12 w-12 place-items-center rounded-2xl bg-[#eff8f2] text-xl font-black text-brand-700">{s.icon}</span>
                <span className="rounded-full bg-slate-50 px-3 py-1 text-[10px] font-bold text-ink-500">{ar ? s.tag.ar : s.tag.en}</span>
              </div>
              <div className="mt-6 text-[10px] font-black tracking-[.18em] text-brand-500">{s.code}</div>
              <h3 className="mt-1 text-xl font-extrabold text-ink-900 transition group-hover:text-brand-700">{ar ? s.title.ar : s.title.en}</h3>
              <p className="mt-3 text-sm leading-7 text-ink-600">{ar ? s.desc.ar : s.desc.en}</p>
              <div className="mt-6 flex items-center justify-between border-t border-slate-100 pt-4 text-xs font-bold text-brand-700"><span>{ar ? "فتح الأداة" : "Open tool"}</span><span className="transition group-hover:translate-x-1 rtl:group-hover:-translate-x-1">→</span></div>
            </Link>
          ))}
        </div>
      </section>

      <section className="container-page pb-20">
        <div className="grid overflow-hidden rounded-[1.75rem] border border-brand-900 bg-[#073722] text-white shadow-[0_24px_70px_rgba(6,44,29,.18)] lg:grid-cols-[1fr_auto] lg:items-center">
          <div className="p-8 sm:p-10">
            <p className="text-xs font-black uppercase tracking-[.18em] text-gold-300">{ar ? "للممول والمستثمر" : "For funders & investors"}</p>
            <h2 className="mt-3 text-2xl font-extrabold sm:text-3xl">{t.investors.title}</h2>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-white/70">{t.investors.body}</p>
          </div>
          <div className="border-t border-white/10 p-8 lg:border-s lg:border-t-0 lg:p-10">
            <Link href="/tools/opportunities" className="inline-flex rounded-xl bg-gold-400 px-6 py-3.5 text-sm font-extrabold text-brand-900 transition hover:bg-gold-300">{t.investors.cta}</Link>
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-amber-200/80 bg-amber-50/80 p-5">
          <h3 className="font-bold text-amber-900">{t.status.title}</h3>
          <p className="mt-1 text-sm leading-6 text-amber-800">{t.status.body}</p>
        </div>
      </section>
    </div>
  );
}
