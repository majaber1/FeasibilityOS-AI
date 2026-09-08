"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import {
  addQualificationRequirement,
  createQualificationProfile,
  getToken,
  listQualificationProfiles,
  listQualificationRequirements,
  updateQualificationRequirement,
  type QualificationProfile,
  type QualificationRequirement,
} from "@/lib/api";
import { useProjectContext } from "@/lib/use-project-context";

const starter = [
  { category: "commercial", title_ar: "سجل تجاري ساري", title_en: "Valid commercial registration", authority: "Ministry of Commerce" },
  { category: "licenses", title_ar: "التراخيص التشغيلية المطلوبة", title_en: "Required operating licenses", authority: "Relevant authority" },
  { category: "saudization", title_ar: "الالتزام بمتطلبات نطاقات", title_en: "Nitaqat compliance", authority: "MHRSD" },
  { category: "funding", title_ar: "قوائم مالية أو توقعات مالية", title_en: "Financial statements or projections", authority: "Funding provider" },
  { category: "tender", title_ar: "ملف المنشأة للمنافسات", title_en: "Tender eligibility file", authority: "Etimad" },
];

export default function QualificationPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<QualificationProfile | null>(null);
  const [requirements, setRequirements] = useState<QualificationRequirement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { project } = useProjectContext();

  const load = useCallback(async (auth: string) => {
    const profiles = await listQualificationProfiles(auth);
    if (!profiles.length) return;
    setProfile(profiles[0]);
    setRequirements(await listQualificationRequirements(auth, profiles[0].id));
  }, []);

  useEffect(() => {
    const auth = getToken();
    setToken(auth);
    if (!auth) { setLoading(false); return; }
    load(auth).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [load]);

  async function create(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!token) return;
    setLoading(true); setError("");
    const data = new FormData(e.currentTarget);
    try {
      const created = await createQualificationProfile(token, {
        company_name_ar: data.get("company_name_ar"),
        company_name_en: data.get("company_name_en"),
        cr_number: data.get("cr_number"),
        sector: data.get("sector"),
        company_size: data.get("company_size"),
      });
      await Promise.all(starter.map((item) => addQualificationRequirement(token, created.id, { ...item, status: "missing", is_mandatory: true, weight: 1 })));
      await load(token);
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed"); }
    finally { setLoading(false); }
  }

  async function change(req: QualificationRequirement, status: string) {
    if (!token || !profile) return;
    try {
      await updateQualificationRequirement(token, profile.id, req.id, status);
      await load(token);
    } catch (e) { setError(e instanceof Error ? e.message : "Request failed"); }
  }

  if (loading) return <main className="container-page py-16"><p>{ar ? "جارٍ التحميل…" : "Loading…"}</p></main>;
  if (!token) return <main className="container-page py-16"><div className="rounded-2xl border bg-white p-8 shadow-card"><h1 className="text-3xl font-bold">{ar ? "التأهيل والجاهزية" : "Qualification & readiness"}</h1><p className="mt-3 text-ink-600">{ar ? "سجّل الدخول لقياس جاهزية منشأتك للتمويل والتراخيص والمنافسات." : "Sign in to assess readiness for funding, licensing, and tenders."}</p><a href="/login" className="mt-6 inline-block rounded-lg bg-brand-600 px-5 py-3 text-white">{ar ? "تسجيل الدخول" : "Sign in"}</a></div></main>;

  return <main className="min-h-screen bg-slate-50 py-12"><div className="container-page">
    <div className="mb-8"><p className="text-sm font-semibold text-brand-700">SAUDI-BUISNESS V1</p><h1 className="mt-2 text-3xl font-bold text-ink-900">{ar ? "تأهيل المنشأة" : "Business qualification"}</h1><p className="mt-2 text-ink-600">{ar ? "تقييم عملي للجاهزية، وليس اعتمادًا رسميًا." : "A practical readiness assessment, not an official certification."}</p></div>
    {error && <p role="alert" className="mb-6 rounded-lg bg-red-50 p-4 text-red-700">{error}</p>}
    {!profile ? <form onSubmit={create} className="grid gap-5 rounded-2xl border bg-white p-7 shadow-card sm:grid-cols-2">
      <h2 className="sm:col-span-2 text-xl font-bold">{ar ? "بيانات المنشأة" : "Business details"}</h2>
      <input required name="company_name_ar" defaultValue={project?.name || ""} placeholder="اسم المنشأة بالعربية" className="rounded-lg border p-3" />
      <input name="company_name_en" placeholder="Company name in English" className="rounded-lg border p-3" />
      <input name="cr_number" placeholder={ar ? "رقم السجل التجاري" : "Commercial registration"} className="rounded-lg border p-3" />
      <input name="sector" defaultValue={project?.industry || ""} placeholder={ar ? "القطاع" : "Sector"} className="rounded-lg border p-3" />
      <select name="company_size" className="rounded-lg border p-3"><option value="micro">{ar ? "متناهية الصغر" : "Micro"}</option><option value="small">{ar ? "صغيرة" : "Small"}</option><option value="medium">{ar ? "متوسطة" : "Medium"}</option></select>
      <button className="rounded-lg bg-brand-600 p-3 font-semibold text-white">{ar ? "إنشاء التقييم" : "Create assessment"}</button>
    </form> : <div className="grid gap-6 lg:grid-cols-[280px,1fr]">
      <aside className="rounded-2xl bg-gradient-to-br from-brand-700 to-brand-900 p-7 text-white shadow-card"><p className="text-sm text-white/70">{ar ? "درجة الجاهزية" : "Readiness score"}</p><p className="mt-3 text-6xl font-bold">{Math.round(profile.overall_score)}<span className="text-xl">%</span></p><p className="mt-4 text-sm text-white/80">{profile.company_name_ar || profile.company_name_en}</p></aside>
      <section className="rounded-2xl border bg-white p-7 shadow-card"><h2 className="text-xl font-bold">{ar ? "قائمة المتطلبات" : "Requirements checklist"}</h2><div className="mt-5 space-y-3">{requirements.map((req) => <div key={req.id} className="flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="font-semibold">{ar ? req.title_ar : req.title_en}</p><p className="text-xs text-ink-600">{req.authority}</p></div><select aria-label={ar ? req.title_ar : req.title_en} value={req.status} onChange={(e) => change(req, e.target.value)} className="rounded-lg border px-3 py-2"><option value="missing">{ar ? "ناقص" : "Missing"}</option><option value="pending">{ar ? "قيد الإجراء" : "Pending"}</option><option value="valid">{ar ? "مكتمل وساري" : "Valid"}</option><option value="expired">{ar ? "منتهي" : "Expired"}</option><option value="not_applicable">{ar ? "لا ينطبق" : "Not applicable"}</option></select></div>)}</div></section>
    </div>}
  </div></main>;
}
