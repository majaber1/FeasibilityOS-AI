"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";

export default function OldFeasibilityRedirect() {
  const router = useRouter();
  const { locale } = useLanguage();
  const ar = locale === "ar";

  useEffect(() => {
    const timer = setTimeout(() => {
      router.push("/projects");
    }, 4000);
    return () => clearTimeout(timer);
  }, [router]);

  return (
    <main className="container-page flex min-h-[60vh] items-center justify-center py-16">
      <div className="mx-auto max-w-lg rounded-2xl border border-brand-200 bg-white p-8 text-center shadow-card">
        <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-xl bg-brand-50 text-2xl">
          📊
        </div>
        <h1 className="text-xl font-bold text-ink-900">
          {ar ? "تم ترقية دراسة الجدوى" : "Feasibility Study Upgraded"}
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-ink-600">
          {ar
            ? "نستخدم الآن محرك الذكاء الاصطناعي V2 لدراسات الجدوى. ستتم إعادة توجيهك إلى صفحة المشاريع حيث يمكنك بدء دراسة جديدة."
            : "We now use the V2 AI engine for feasibility studies. You'll be redirected to the projects page where you can start a new study."}
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            href="/projects"
            className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-700"
          >
            {ar ? "الذهاب إلى المشاريع" : "Go to Projects"}
          </Link>
          <Link
            href="/dashboard"
            className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-ink-700 hover:border-brand-500"
          >
            {ar ? "لوحة التحكم" : "Dashboard"}
          </Link>
        </div>
        <p className="mt-4 text-xs text-ink-400">
          {ar ? "سيتم إعادة التوجيه تلقائياً..." : "Redirecting automatically..."}
        </p>
      </div>
    </main>
  );
}
