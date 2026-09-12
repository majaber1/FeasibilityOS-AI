"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";

export function Footer() {
  const { t, locale } = useLanguage();
  const ar = locale === "ar";
  const year = new Date().getFullYear();

  const columns = [
    {
      title: ar ? "الأدوات" : "Tools",
      links: [
        { href: "/tools/feasibility", label: ar ? "دراسة الجدوى" : "Feasibility Study" },
        { href: "/tools/feasibility", label: ar ? "التحليل المالي (ضمن الدراسة)" : "Financial Analysis (in study)" },
        { href: "/tools/proposal", label: ar ? "منشئ العروض" : "Proposal Builder" },
        { href: "/tools/funding", label: ar ? "مطابقة التمويل" : "Funding Matcher" },
        { href: "/tools/qualification", label: ar ? "تأهيل الأعمال" : "Qualification" },
      ],
    },
    {
      title: t.footer.forInvestors,
      links: [
        { href: "/opportunities", label: ar ? "الفرص الاستثمارية" : "Opportunities" },
        { href: "/tools/franchise", label: ar ? "الامتياز التجاري" : "Franchise" },
      ],
    },
    {
      title: t.footer.company,
      links: [
        { href: "/pricing", label: t.footer.links.pricing },
        { href: "/help", label: t.footer.links.help },
        { href: "/tools/reports", label: ar ? "التقارير" : "Reports" },
        { href: "https://github.com/majaber1/saudi-business", label: t.footer.links.source },
      ],
    },
  ];

  return (
    <footer className="border-t border-slate-200 bg-slate-50">
      <div className="container-page grid gap-10 py-14 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-brand-600 to-brand-800 font-bold text-white">
              {t.brand[0]}
            </span>
            <span className="font-semibold text-ink-900">{t.brand}</span>
          </div>
          <p className="mt-4 max-w-xs text-sm text-ink-600">{t.tagline}</p>
          <p className="mt-3 text-xs text-ink-500">
            {ar ? "من فكرة المشروع إلى جاهزية الاستثمار" : "From business idea to investment-ready"}
          </p>
        </div>

        {columns.map((col) => (
          <div key={col.title}>
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-500">{col.title}</h3>
            <ul className="mt-4 space-y-2.5 text-sm text-ink-700">
              {col.links.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="hover:text-brand-600">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="border-t border-slate-200">
        <div className="container-page flex flex-col gap-2 py-6 text-sm text-ink-600 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-2xl text-ink-500">{t.footer.disclaimer}</p>
          <p className="whitespace-nowrap text-ink-500">
            © {year} {t.brand} — {t.footer.rights}
          </p>
        </div>
      </div>
    </footer>
  );
}
