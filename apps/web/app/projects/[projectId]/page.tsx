"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";
import { createStudy, getProject, getToken, listStudies, updateProject, type Project, type Study } from "@/lib/api";
import { useLanguage } from "@/components/LanguageProvider";

export default function ProjectWorkspacePage({ params }: { params: Promise<{ projectId: string }> }) {
  const { projectId: rawProjectId } = use(params);
  const projectId = Number(rawProjectId);
  const { locale } = useLanguage();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [study, setStudy] = useState<Study | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("");
  const [investment, setInvestment] = useState(0);
  const [stage, setStage] = useState("idea");
  const token = getToken();

  useEffect(() => {
    if (!token || !Number.isInteger(projectId)) { setLoading(false); return; }
    Promise.all([getProject(token, projectId), listStudies(token, projectId)])
      .then(([projectRow, studies]) => {
        setProject(projectRow);
        setStudy(studies[0] ?? null);
        setName(projectRow.name);
        setIndustry(projectRow.industry);
        setInvestment(projectRow.investment);
        setStage(projectRow.stage);
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)))
      .finally(() => setLoading(false));
  }, [projectId, token]);

  async function startStudy() {
    if (!token || !project || creating) return;
    setCreating(true); setError("");
    try {
      const existing = (await listStudies(token, project.id))[0];
      const target = existing ?? await createStudy(token, { title: project.name, industry: project.industry, investment: project.investment, project_id: project.id, study_type: "business_decision" });
      router.push(`/projects/${project.id}/studies/${target.id}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); setCreating(false); }
  }

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !project) return;
    setError("");
    try {
      const saved = await updateProject(token, project.id, { name, industry, investment, stage });
      setProject(saved);
      setEditing(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }

  if (!token) return <main className="container-page py-16"><p>{locale === "ar" ? "سجّل الدخول لفتح هذا المشروع." : "Sign in to open this project."}</p><Link className="mt-4 inline-flex rounded-lg bg-brand-600 px-4 py-2 text-white" href={`/login?next=${encodeURIComponent(`/projects/${projectId}`)}`}>{locale === "ar" ? "تسجيل الدخول" : "Sign in"}</Link></main>;
  if (loading) return <main className="container-page py-16">{locale === "ar" ? "جارٍ تحميل المشروع..." : "Loading project..."}</main>;
  if (error || !project) return <main className="container-page py-16"><p role="alert" className="rounded-lg bg-red-50 p-4 text-red-700">{error || (locale === "ar" ? "تعذر العثور على المشروع." : "Project not found.")}</p></main>;

  return <main className="container-page py-12" data-testid="project-workspace"><Link href="/projects" className="text-sm text-brand-700">{locale === "ar" ? "العودة إلى المشاريع" : "Back to projects"}</Link><section className="mt-5 rounded-2xl border border-slate-200 bg-white p-7 shadow-sm"><p className="text-sm text-ink-500">{locale === "ar" ? "مساحة المشروع" : "Project workspace"}</p><h1 className="mt-1 text-3xl font-bold" data-testid="project-workspace-title">{project.name}</h1><p className="mt-3 text-ink-600">{new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-SA", { style: "currency", currency: "SAR", maximumFractionDigits: 0 }).format(project.investment)}</p>
    {editing ? (
      <form onSubmit={(e) => void saveProfile(e)} className="mt-6 grid gap-3 sm:grid-cols-2" data-testid="project-profile-form">
        <label className="text-sm">{locale === "ar" ? "اسم المشروع" : "Project name"}<input required value={name} onChange={(e) => setName(e.target.value)} data-testid="project-profile-name" className="mt-1 w-full rounded-lg border px-3 py-2" /></label>
        <label className="text-sm">{locale === "ar" ? "القطاع" : "Sector"}<input required value={industry} onChange={(e) => setIndustry(e.target.value)} data-testid="project-profile-industry" className="mt-1 w-full rounded-lg border px-3 py-2" /></label>
        <label className="text-sm">{locale === "ar" ? "الميزانية" : "Budget"}<input type="number" min={1} required value={investment} onChange={(e) => setInvestment(Number(e.target.value))} data-testid="project-profile-investment" className="mt-1 w-full rounded-lg border px-3 py-2" /></label>
        <label className="text-sm">{locale === "ar" ? "المرحلة" : "Stage"}<input required value={stage} onChange={(e) => setStage(e.target.value)} data-testid="project-profile-stage" className="mt-1 w-full rounded-lg border px-3 py-2" /></label>
        <div className="flex gap-2 sm:col-span-2">
          <button type="submit" data-testid="save-project-profile" className="rounded-lg bg-brand-600 px-4 py-2 text-white">{locale === "ar" ? "حفظ الملف" : "Save profile"}</button>
          <button type="button" onClick={() => setEditing(false)} className="rounded-lg border px-4 py-2">{locale === "ar" ? "إلغاء" : "Cancel"}</button>
        </div>
      </form>
    ) : (
      <button type="button" onClick={() => setEditing(true)} data-testid="edit-project-profile" className="mt-4 rounded-lg border px-4 py-2 text-sm">{locale === "ar" ? "تعديل معلومات المشروع" : "Edit project information"}</button>
    )}
    <div className="mt-7">{study ? <Link href={`/projects/${project.id}/studies/${study.id}`} data-testid="continue-existing-study" className="inline-flex rounded-lg bg-brand-600 px-5 py-3 font-medium text-white">{study.status === "completed" ? (locale === "ar" ? "عرض القرار" : "View decision") : (locale === "ar" ? "متابعة الدراسة" : "Continue study")}</Link> : <button onClick={() => void startStudy()} disabled={creating} data-testid="start-study-btn" className="rounded-lg bg-brand-600 px-5 py-3 font-medium text-white disabled:opacity-60">{creating ? (locale === "ar" ? "جارٍ الإنشاء..." : "Creating...") : (locale === "ar" ? "ابدأ الدراسة" : "Start study")}</button>}</div></section></main>;
}
