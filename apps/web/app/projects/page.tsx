"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createProject, getToken, listProjects, listStudies, listV2Studies, findV2StudyForProject, setProjectArchived, updateProject, type Project, type Study, type V2StudySummary } from "@/lib/api";
import { useLanguage } from "@/components/LanguageProvider";

const INDUSTRIES = ["technology", "retail", "food", "healthcare", "industrial", "tourism", "education"];
const copy = {
  ar: { title: "مشاريعي", intro: "احتفظ بأفكارك ومشاريعك في مكان واحد، وابدأ بالمعلومات الأساسية فقط.", add: "إضافة مشروع", name: "اسم المشروع", industry: "القطاع", investment: "الميزانية التقديرية (ر.س)", stage: "المرحلة", idea: "فكرة", mvp: "نموذج أولي", revenue: "إيرادات مبكرة", growth: "نمو", save: "حفظ المشروع", empty: "لا يوجد لديك مشروع حتى الآن.", emptyBody: "أضف فكرتك الأولى وسنساعدك على دراستها خطوة بخطوة.", active: "الحالية", archived: "المؤرشفة", edit: "تعديل", archive: "أرشفة", restore: "استعادة", startStudy: "ابدأ الدراسة", continueStudy: "متابعة الدراسة", viewDecision: "عرض القرار", cancel: "إلغاء", login: "سجّل الدخول لعرض مشاريعك.", loading: "جارٍ التحميل..." },
  en: { title: "My projects", intro: "Keep your ideas and businesses in one place. Start with only the essentials.", add: "Add project", name: "Project name", industry: "Sector", investment: "Estimated budget (SAR)", stage: "Stage", idea: "Idea", mvp: "MVP", revenue: "Early revenue", growth: "Growth", save: "Save project", empty: "You do not have a project yet.", emptyBody: "Add your first idea and we will help you assess it step by step.", active: "Current", archived: "Archived", edit: "Edit", archive: "Archive", restore: "Restore", startStudy: "Start study", continueStudy: "Continue study", viewDecision: "View decision", cancel: "Cancel", login: "Sign in to view your projects.", loading: "Loading..." },
};

export default function ProjectsPage() {
  const router = useRouter();
  const { locale } = useLanguage(); const c = copy[locale];
  const [projects, setProjects] = useState<Project[] | null>(null); const [showArchived, setShowArchived] = useState(false);
  const [studiesByProject, setStudiesByProject] = useState<Record<number, Study>>({});
  const [v2ByProject, setV2ByProject] = useState<Record<number, V2StudySummary>>({});
  const [showForm, setShowForm] = useState(false); const [editing, setEditing] = useState<Project | null>(null);
  const [name, setName] = useState(""); const [industry, setIndustry] = useState("technology"); const [investment, setInvestment] = useState(100000); const [stage, setStage] = useState("idea");
  const [error, setError] = useState<string | null>(null); const [token, setToken] = useState<string | null>(null);

  async function load(archived = showArchived) {
    if (!token) return;
    setError(null);
    try {
      const rows = (await listProjects(token, archived)).filter((p) => p.is_archived === archived);
      setProjects(rows);
      const [groups, v2Studies] = await Promise.all([
        Promise.all(rows.map(async (project) => [project.id, (await listStudies(token, project.id))[0]] as const)),
        listV2Studies(token),
      ]);
      setStudiesByProject(Object.fromEntries(groups.filter((entry): entry is readonly [number, Study] => Boolean(entry[1]))));
      const v2Map: Record<number, V2StudySummary> = {};
      for (const row of rows) {
        const hit = findV2StudyForProject(v2Studies, row.id);
        if (hit) v2Map[row.id] = hit;
      }
      setV2ByProject(v2Map);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }
  useEffect(() => { setToken(getToken()); }, []);
  useEffect(() => { if (token) void load(false); }, [token]); // eslint-disable-line react-hooks/exhaustive-deps
  function reset() { setEditing(null); setName(""); setIndustry("technology"); setInvestment(100000); setStage("idea"); setShowForm(false); }
  function beginEdit(p: Project) { setEditing(p); setName(p.name); setIndustry(p.industry); setInvestment(p.investment); setStage(p.stage); setShowForm(true); }
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setError(null);
    try {
      if (editing) {
        await updateProject(token, editing.id, { name, industry, investment, stage });
        reset();
        await load();
      } else {
        const created = await createProject(token, { name, industry, investment, stage });
        router.push(`/projects/${created.id}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }
  async function toggleArchive(p: Project) { if (!token) return; try { await setProjectArchived(token, p.id, !p.is_archived); await load(); } catch (err) { setError(err instanceof Error ? err.message : String(err)); } }

  if (!token) return <main className="container-page py-16"><h1 className="text-3xl font-bold">{c.title}</h1><p className="mt-3">{c.login}</p><Link href="/login" className="mt-5 inline-flex rounded-lg bg-brand-600 px-5 py-2.5 text-white">{locale === "ar" ? "تسجيل الدخول" : "Sign in"}</Link></main>;
  return <main className="container-page py-12" data-testid="projects-workspace"><div className="flex flex-wrap items-end justify-between gap-4"><div><h1 className="text-3xl font-bold text-ink-900">{c.title}</h1><p className="mt-2 text-ink-600">{c.intro}</p></div><button onClick={() => setShowForm(true)} data-testid="add-project-btn" className="rounded-lg bg-brand-600 px-5 py-2.5 font-medium text-white">{c.add}</button></div>
    <div className="mt-8 flex gap-2"><button onClick={() => { setShowArchived(false); void load(false); }} className={!showArchived ? "rounded-full bg-ink-900 px-4 py-2 text-sm text-white" : "rounded-full bg-slate-100 px-4 py-2 text-sm"}>{c.active}</button><button onClick={() => { setShowArchived(true); void load(true); }} className={showArchived ? "rounded-full bg-ink-900 px-4 py-2 text-sm text-white" : "rounded-full bg-slate-100 px-4 py-2 text-sm"}>{c.archived}</button></div>
    {error && <p role="alert" className="mt-5 rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</p>}
    {showForm && <form onSubmit={submit} data-testid="project-form" className="mt-6 grid gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:grid-cols-2"><label className="text-sm">{c.name}<input required maxLength={200} value={name} onChange={(e) => setName(e.target.value)} data-testid="project-name-input" className="mt-1 w-full rounded-lg border px-3 py-2" /></label><label className="text-sm">{c.industry}<select value={industry} onChange={(e) => setIndustry(e.target.value)} data-testid="project-industry-select" className="mt-1 w-full rounded-lg border bg-white px-3 py-2">{INDUSTRIES.map((x) => <option key={x}>{x}</option>)}</select></label><label className="text-sm">{c.investment}<input type="number" min={1} required value={investment} onChange={(e) => setInvestment(Number(e.target.value))} data-testid="project-investment-input" className="mt-1 w-full rounded-lg border px-3 py-2" /></label><label className="text-sm">{c.stage}<select value={stage} onChange={(e) => setStage(e.target.value)} data-testid="project-stage-select" className="mt-1 w-full rounded-lg border bg-white px-3 py-2"><option value="idea">{c.idea}</option><option value="mvp">{c.mvp}</option><option value="early_revenue">{c.revenue}</option><option value="growth">{c.growth}</option></select></label><div className="flex gap-3 sm:col-span-2"><button data-testid="save-project-btn" className="rounded-lg bg-brand-600 px-5 py-2.5 text-white">{c.save}</button><button type="button" onClick={reset} className="rounded-lg border px-5 py-2.5">{c.cancel}</button></div></form>}
    {projects === null ? <p className="py-12 text-center">{c.loading}</p> : projects.length === 0 ? <section className="mt-8 rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center"><h2 className="text-xl font-semibold">{c.empty}</h2><p className="mt-2 text-ink-600">{c.emptyBody}</p><button onClick={() => setShowForm(true)} data-testid="add-project-empty" className="mt-5 rounded-lg bg-brand-600 px-5 py-2.5 text-white">{c.add}</button></section> : <div className="mt-8 grid gap-4 md:grid-cols-2">{projects.map((p) => { const study = studiesByProject[p.id]; const href = study ? `/projects/${p.id}/studies/${study.id}` : `/projects/${p.id}`; const label = !study ? c.startStudy : study.status === "completed" ? c.viewDecision : c.continueStudy; return <article key={p.id} data-testid={`project-card-${p.id}`} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex items-start justify-between gap-4"><div><Link href={`/projects/${p.id}`} data-testid={`open-project-${p.id}`} className="text-lg font-semibold hover:text-brand-700">{p.name}</Link><p className="mt-1 text-sm text-ink-600">{p.industry} · {new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-US").format(p.investment)} {locale === "ar" ? "ر.س" : "SAR"}</p></div><span className="rounded-full bg-slate-100 px-3 py-1 text-xs">{p.stage}</span></div><div className="mt-5 flex flex-wrap gap-2">{!p.is_archived && <Link href={v2ByProject[p.id] ? `/projects/${p.id}/studies/${v2ByProject[p.id].study_id}/workspace` : `/projects/${p.id}/studies/new/workspace`} data-testid={`ai-study-${p.id}`} className="rounded-lg bg-brand-600 px-3 py-2 text-sm text-white">{v2ByProject[p.id] ? (locale === "ar" ? "متابعة دراسة AI" : "Continue AI study") : (locale === "ar" ? "دراسة AI" : "AI study")}</Link>}{!p.is_archived && <Link href={href} data-testid={`continue-study-${p.id}`} className="rounded-lg border px-3 py-2 text-sm">{label}</Link>}<button onClick={() => beginEdit(p)} data-testid={`edit-project-${p.id}`} className="rounded-lg border px-3 py-2 text-sm">{c.edit}</button><button onClick={() => void toggleArchive(p)} className="rounded-lg border px-3 py-2 text-sm">{p.is_archived ? c.restore : c.archive}</button></div></article>; })}</div>}
  </main>;
}
