"use client";

import { useEffect, useState } from "react";
import { API_BASE, getToken } from "@/lib/api";
import { useLanguage } from "@/components/LanguageProvider";
import { archetypeLabel } from "@/lib/archetypeLabels";

type Dashboard = {
  documents_count: number;
  memories_count: number;
  average_quality_score: number | null;
  coverage: { sector: string; count: number }[];
  quality_scores: {
    id: string;
    title: string;
    quality_score: number | null;
    reasons?: string[];
    project_type?: string | null;
    sector?: string | null;
    year?: number | null;
  }[];
  most_referenced: {
    id: string;
    title: string;
    reference_count: number;
    quality_score: number | null;
    project_type?: string | null;
  }[];
  recent_memories: {
    id: string;
    source_study_id: string;
    archetype?: string | null;
    sector?: string | null;
    summary_text?: string | null;
  }[];
};

export default function KnowledgeDashboardPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setError(ar ? "يلزم تسجيل الدخول" : "Login required");
      setLoading(false);
      return;
    }
    void (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v2/knowledge/dashboard`, {
          headers: { Authorization: `Bearer ${token}` },
          credentials: "same-origin",
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        setData(json.dashboard || null);
      } catch (e: any) {
        setError(e?.message || "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    })();
  }, [ar]);

  return (
    <div className="min-h-screen bg-[#f5f7f6]" data-testid="knowledge-dashboard-page">
      <section className="border-b border-slate-200 bg-white">
        <div className="container-page py-10">
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-teal-700">
            {ar ? "طبقة المعرفة" : "Knowledge Intelligence"}
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-ink-900">
            {ar ? "لوحة معرفة المشاريع" : "Knowledge Dashboard"}
          </h1>
          <p className="mt-2 max-w-2xl text-ink-600">
            {ar
              ? "جودة الوثائق، تغطية القطاعات، والمراجع الأكثر استخدامًا في الافتراضات."
              : "Document quality, sector coverage, and the most-referenced evidence behind assumptions."}
          </p>
        </div>
      </section>

      <div className="container-page py-8">
        {loading ? (
          <p className="text-sm text-ink-500">{ar ? "جارٍ التحميل…" : "Loading…"}</p>
        ) : null}
        {error ? (
          <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800" data-testid="knowledge-dashboard-error">
            {error}
          </p>
        ) : null}

        {data ? (
          <div className="space-y-8">
            <div className="grid gap-4 sm:grid-cols-3" data-testid="knowledge-dashboard-stats">
              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                <p className="text-xs uppercase tracking-wide text-ink-500">{ar ? "الوثائق" : "Documents"}</p>
                <p className="mt-2 text-3xl font-bold text-ink-900">{data.documents_count}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                <p className="text-xs uppercase tracking-wide text-ink-500">{ar ? "الذكريات" : "Study memories"}</p>
                <p className="mt-2 text-3xl font-bold text-ink-900">{data.memories_count}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white p-5">
                <p className="text-xs uppercase tracking-wide text-ink-500">{ar ? "متوسط الجودة" : "Avg quality"}</p>
                <p className="mt-2 text-3xl font-bold text-teal-800">
                  {data.average_quality_score != null ? `${Math.round(data.average_quality_score)}%` : "—"}
                </p>
              </div>
            </div>

            <section>
              <h2 className="mb-3 text-lg font-semibold text-ink-900">
                {ar ? "التغطية حسب القطاع" : "Coverage by sector"}
              </h2>
              {data.coverage.length === 0 ? (
                <p className="text-sm text-ink-500">{ar ? "لا توجد تغطية بعد." : "No coverage yet."}</p>
              ) : (
                <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3" data-testid="knowledge-coverage">
                  {data.coverage.map((c) => (
                    <li key={c.sector} className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
                      <span className="font-medium text-ink-900">{c.sector}</span>
                      <span className="float-right text-ink-500">{c.count}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h2 className="mb-3 text-lg font-semibold text-ink-900">
                {ar ? "درجات الجودة" : "Quality scores"}
              </h2>
              <ul className="space-y-2" data-testid="knowledge-quality-list">
                {data.quality_scores.map((q) => (
                  <li key={q.id} className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium text-ink-900">{q.title}</p>
                      <span className="rounded-md bg-teal-100 px-2 py-0.5 text-xs font-semibold text-teal-900">
                        {q.quality_score != null ? `${Math.round(q.quality_score)}%` : "—"}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-ink-500">
                      {[q.project_type, q.sector, q.year].filter(Boolean).join(" · ")}
                    </p>
                    {(q.reasons || []).length > 0 ? (
                      <p className="mt-1 text-xs text-teal-800">{(q.reasons || []).slice(0, 3).join(" · ")}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>

            <section>
              <h2 className="mb-3 text-lg font-semibold text-ink-900">
                {ar ? "الأكثر مرجعية" : "Most referenced"}
              </h2>
              <ul className="space-y-2" data-testid="knowledge-most-referenced">
                {data.most_referenced.map((r) => (
                  <li key={r.id} className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-medium text-ink-900">{r.title}</p>
                      <span className="text-xs text-ink-500">
                        {r.reference_count} {ar ? "مرجع" : "refs"}
                        {r.quality_score != null ? ` · ${Math.round(r.quality_score)}%` : ""}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </section>

            <section>
              <h2 className="mb-3 text-lg font-semibold text-ink-900">
                {ar ? "ذكريات حديثة" : "Recent study memories"}
              </h2>
              <ul className="space-y-2" data-testid="knowledge-recent-memories">
                {data.recent_memories.map((m) => (
                  <li key={m.id} className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm">
                    <p className="font-medium text-ink-900">{m.source_study_id}</p>
                    <p className="mt-1 text-xs text-ink-500">
                      {[m.archetype ? archetypeLabel(m.archetype, ar ? "ar" : "en") : null, m.sector]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                    {m.summary_text ? <p className="mt-1 text-xs text-ink-600">{m.summary_text}</p> : null}
                  </li>
                ))}
              </ul>
            </section>
          </div>
        ) : null}
      </div>
    </div>
  );
}
