"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useLanguage } from "@/components/LanguageProvider";
import { ServiceHeader } from "@/components/ui/ServiceHeader";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Field, Input, Select } from "@/components/ui/Input";
import { createStudy, getToken, listProjects, type Project } from "@/lib/api";

const INDUSTRIES = [
  { value: "technology", ar: "تقنية", en: "Technology" },
  { value: "logistics", ar: "خدمات لوجستية", en: "Logistics" },
  { value: "food_beverage", ar: "أغذية ومشروبات", en: "Food & Beverage" },
  { value: "healthcare", ar: "رعاية صحية", en: "Healthcare" },
  { value: "manufacturing", ar: "تصنيع", en: "Manufacturing" },
  { value: "retail", ar: "تجزئة", en: "Retail" },
  { value: "education", ar: "تعليم", en: "Education" },
  { value: "other", ar: "أخرى", en: "Other" },
];

export default function NewFeasibilityPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [mode, setMode] = useState<"existing" | "standalone">("standalone");
  const [projectId, setProjectId] = useState("");
  const [title, setTitle] = useState("");
  const [industry, setIndustry] = useState("technology");
  const [investment, setInvestment] = useState("");
  const [studyType, setStudyType] = useState("general");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    listProjects(token).then(setProjects).catch(() => undefined);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const selected = mode === "existing" ? projects.find((p) => String(p.id) === projectId) : undefined;
      const study = await createStudy(token, {
        title: title.trim() || selected?.name || (ar ? "دراسة جدوى" : "Feasibility study"),
        industry: selected?.industry || industry,
        investment: selected ? Number(selected.investment) : Number(investment),
        study_type: studyType,
        project_id: selected?.id,
      });
      router.push(`/projects/${study.project_id}/studies/${study.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <ServiceHeader
        icon="📊"
        title={ar ? "دراسة جدوى جديدة" : "New Feasibility Study"}
        subtitle={ar ? "ابدأ من مشروع قائم أو أنشئ دراسة مستقلة. لا تحتاج إلى إكمال أدوات أخرى أولاً." : "Start from an existing business or a standalone study. Other tools are not required first."}
        breadcrumb={[
          { label: ar ? "الأدوات" : "Tools", href: "/tools" },
          { label: ar ? "دراسة الجدوى" : "Feasibility", href: "/tools/feasibility" },
        ]}
      />
      <form onSubmit={handleSubmit} className="container-page max-w-3xl space-y-6 py-8">
        {error && <Alert tone="danger">{error}</Alert>}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          <h2 className="text-lg font-bold text-ink-900">{ar ? "كيف تريد أن تبدأ؟" : "How do you want to start?"}</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <button type="button" onClick={() => setMode("standalone")} className={`rounded-xl border p-4 text-start ${mode === "standalone" ? "border-brand-500 bg-brand-50" : "border-slate-200"}`}>
              <p className="font-bold">{ar ? "دراسة مستقلة" : "Standalone study"}</p>
              <p className="mt-1 text-sm text-ink-600">{ar ? "أنشئ سياقاً تجارياً جديداً لهذه الدراسة فقط." : "Create a new business context for this study only."}</p>
            </button>
            <button type="button" onClick={() => setMode("existing")} className={`rounded-xl border p-4 text-start ${mode === "existing" ? "border-brand-500 bg-brand-50" : "border-slate-200"}`}>
              <p className="font-bold">{ar ? "ربط بعمل قائم" : "Link an existing business"}</p>
              <p className="mt-1 text-sm text-ink-600">{ar ? "استخدم الاسم والقطاع والاستثمار المحفوظين." : "Reuse the saved name, sector, and investment."}</p>
            </button>
          </div>
        </section>
        {mode === "existing" ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
            <Field label={ar ? "العمل / المشروع" : "Business / project"}>
              <Select value={projectId} onChange={(e) => setProjectId(e.target.value)} required>
                <option value="">{ar ? "اختر مشروعاً" : "Select a project"}</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </Select>
            </Field>
          </section>
        ) : (
          <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
            <Field label={ar ? "اسم المشروع" : "Business name"}>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} required data-testid="feasibility-title" />
            </Field>
            <Field label={ar ? "القطاع" : "Sector"}>
              <Select value={industry} onChange={(e) => setIndustry(e.target.value)} data-testid="feasibility-industry">
                {INDUSTRIES.map((i) => <option key={i.value} value={i.value}>{ar ? i.ar : i.en}</option>)}
              </Select>
            </Field>
            <Field label={ar ? "الاستثمار المتوقع (ر.س)" : "Expected investment (SAR)"}>
              <Input type="number" min="1" value={investment} onChange={(e) => setInvestment(e.target.value)} required data-testid="feasibility-investment" />
            </Field>
          </section>
        )}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          <Field label={ar ? "نوع الدراسة" : "Study type"}>
            <Select value={studyType} onChange={(e) => setStudyType(e.target.value)}>
              <option value="general">{ar ? "عامة" : "General"}</option>
              <option value="startup">{ar ? "شركة ناشئة" : "Startup"}</option>
              <option value="expansion">{ar ? "توسع" : "Expansion"}</option>
              <option value="franchise">{ar ? "امتياز تجاري" : "Franchise"}</option>
            </Select>
          </Field>
        </section>
        <Button type="submit" disabled={saving} data-testid="start-feasibility">
          {saving ? (ar ? "جارٍ الإنشاء..." : "Creating...") : (ar ? "ابدأ الدراسة" : "Start study")}
        </Button>
      </form>
    </div>
  );
}
