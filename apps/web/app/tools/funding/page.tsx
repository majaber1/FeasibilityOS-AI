"use client";

import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { ServiceHeader } from "@/components/ui/ServiceHeader";
import { Badge } from "@/components/ui/Badge";
import { getToken, listFundingDocuments, matchFunding, uploadFundingDocument, type FundingDocument, type FundingMatch } from "@/lib/api";
import { useProjectContext } from "@/lib/use-project-context";

const industries = [
  { value: "technology", ar: "تقنية", en: "Technology" },
  { value: "food_beverage", ar: "أغذية ومشروبات", en: "Food & Beverage" },
  { value: "healthcare", ar: "رعاية صحية", en: "Healthcare" },
  { value: "manufacturing", ar: "تصنيع", en: "Manufacturing" },
  { value: "retail", ar: "تجزئة", en: "Retail" },
  { value: "logistics", ar: "خدمات لوجستية", en: "Logistics" },
  { value: "education", ar: "تعليم", en: "Education" },
  { value: "energy", ar: "طاقة", en: "Energy" },
  { value: "real_estate", ar: "عقارات", en: "Real Estate" },
  { value: "other", ar: "أخرى", en: "Other" },
];

const stages = [
  { value: "idea", ar: "فكرة", en: "Idea" },
  { value: "mvp", ar: "منتج أولي", en: "MVP" },
  { value: "early_revenue", ar: "إيرادات أولية", en: "Early Revenue" },
  { value: "growth", ar: "نمو", en: "Growth" },
];

const fundingPrograms: Record<string, { ar: string; url?: string }> = {
  RDIA: { ar: "هيئة تنمية البحث والتطوير والابتكار", url: "https://rdia.gov.sa" },
  MONSHAAT: { ar: "الهيئة العامة للمنشآت الصغيرة والمتوسطة (منشآت)", url: "https://www.monshaat.gov.sa" },
  KAFALAH: { ar: "برنامج كفالة لضمان التمويل", url: "https://www.kafalah.gov.sa/ar/Pages/default.aspx" },
  NTDP: { ar: "البرنامج الوطني لتنمية تقنية المعلومات", url: "https://ntdp.gov.sa" },
  CODE: { ar: "مركز ريادة الأعمال الرقمية" },
  SVC: { ar: "الشركة السعودية للاستثمار الجريء", url: "https://svc.com.sa" },
};

function localizeMatch(text: string, ar: boolean) {
  if (!ar) return text;
  return text
    .replace(/Industry '([^']+)' matches (.+) focus areas/, "القطاع المختار ضمن مجالات تركيز البرنامج")
    .replace(/Industry '([^']+)' is outside (.+) typical focus/, "القطاع المختار خارج نطاق التركيز المعتاد للبرنامج")
    .replace(/(.+) supports general\/cross-sector SMEs/, "البرنامج يدعم المنشآت الصغيرة والمتوسطة في قطاعات متعددة")
    .replace(/Project stage '([^']+)' is within (.+)'s supported range/, "مرحلة المشروع ضمن المراحل التي يدعمها البرنامج")
    .replace(/Stage '([^']+)' is not typically funded by (.+)/, "مرحلة المشروع ليست ضمن المراحل التي يمولها البرنامج عادةً")
    .replace("MVP validation strengthens the application", "وجود منتج أولي يعزز ملف الطلب")
    .replace("MVP validation not yet available", "لا يتوفر منتج أولي موثّق بعد")
    .replace("Technical team in place", "الفريق التقني متوفر")
    .replace("Technical team requirements not yet met", "متطلبات الفريق التقني غير مكتملة بعد");
}

export default function FundingMatcherPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const [industry, setIndustry] = useState("");
  const [stage, setStage] = useState("");
  const [hasMvp, setHasMvp] = useState(false);
  const [hasTeam, setHasTeam] = useState(false);
  const [requestedAmount, setRequestedAmount] = useState("");
  const [annualRevenue, setAnnualRevenue] = useState("");
  const [annualExpenses, setAnnualExpenses] = useState("");
  const [existingDebt, setExistingDebt] = useState("0");
  const [employees, setEmployees] = useState("");
  const [purpose, setPurpose] = useState("");
  const [hasCr, setHasCr] = useState(false);
  const [hasFinancials, setHasFinancials] = useState(false);
  const [hasBankStatements, setHasBankStatements] = useState(false);
  const [hasLicense, setHasLicense] = useState(false);
  const [results, setResults] = useState<FundingMatch[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [documents, setDocuments] = useState<FundingDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const { project, error: projectError } = useProjectContext();

  useEffect(() => {
    if (!project) return;
    setIndustry(project.industry);
    setStage(project.stage);
    setHasMvp(project.stage !== "idea");
    setRequestedAmount(String(project.investment));
  }, [project]);

  useEffect(() => {
    const token = getToken();
    if (project && token) listFundingDocuments(token, project.id).then(setDocuments).catch(() => undefined);
  }, [project]);

  async function handleDocument(file?: File) {
    const token = getToken();
    if (!file || !project || !token) { setError(ar ? "سجّل الدخول واختر مشروعًا قبل رفع المستند." : "Sign in and select a project before uploading."); return; }
    setUploading(true); setError("");
    try { const saved = await uploadFundingDocument(token, project.id, file); setDocuments((current) => [saved, ...current]); }
    catch (err) { setError(err instanceof Error ? err.message : String(err)); }
    finally { setUploading(false); }
  }

  const readinessChecks = [Boolean(industry), Boolean(stage), Number(requestedAmount) > 0, Number(annualRevenue) > 0, Number(annualExpenses) >= 0, Number(existingDebt) >= 0, Number(employees) >= 0, Boolean(purpose.trim()), hasCr, hasFinancials, hasBankStatements, hasLicense];
  const readinessScore = Math.round((readinessChecks.filter(Boolean).length / readinessChecks.length) * 100);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!industry) { setError(ar ? "اختر القطاع" : "Select an industry"); return; }
    setError("");
    setLoading(true);
    try {
      const r = await matchFunding({ industry, stage: stage || undefined, has_mvp: hasMvp, has_technical_team: hasTeam });
      setResults(r);
    } catch {
      setError(ar ? "حدث خطأ" : "An error occurred");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <ServiceHeader
        icon="🏦"
        title={ar ? "مطابقة التمويل" : "Funding Matcher"}
        subtitle={ar ? "مطابقة شفّافة مع برامج التمويل السعودية الرسمية" : "Transparent matching with official Saudi funding programs"}
        breadcrumb={[{ label: ar ? "الأدوات" : "Tools", href: "/tools" }]}
      />

      <div className="container-page space-y-8 py-8">
        {project && (
          <div className="rounded-xl border border-brand-200 bg-brand-50 px-5 py-4 text-sm text-brand-800">
            {ar ? "تمت تعبئة بيانات المشروع:" : "Project data loaded:"} <strong>{project.name}</strong>
          </div>
        )}
        {projectError && <p role="alert" className="rounded-xl bg-red-50 p-4 text-sm text-red-700">{projectError}</p>}
        <div className="grid gap-8 lg:grid-cols-[400px_1fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
            <h2 className="text-lg font-bold text-ink-900">{ar ? "بيانات المطابقة" : "Matching criteria"}</h2>

            <form onSubmit={handleSubmit} className="mt-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-ink-700">{ar ? "القطاع" : "Industry"}</label>
                <select value={industry} onChange={(e) => setIndustry(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-brand-500 focus:outline-none">
                  <option value="">{ar ? "اختر القطاع" : "Select industry"}</option>
                  {industries.map((i) => <option key={i.value} value={i.value}>{ar ? i.ar : i.en}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-sm text-ink-700">{ar ? "التمويل المطلوب" : "Requested funding"}<input type="number" min="1" value={requestedAmount} onChange={(e) => setRequestedAmount(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="text-sm text-ink-700">{ar ? "عدد الموظفين" : "Employees"}<input type="number" min="0" value={employees} onChange={(e) => setEmployees(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="text-sm text-ink-700">{ar ? "الإيراد السنوي" : "Annual revenue"}<input type="number" min="0" value={annualRevenue} onChange={(e) => setAnnualRevenue(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="text-sm text-ink-700">{ar ? "المصاريف السنوية" : "Annual expenses"}<input type="number" min="0" value={annualExpenses} onChange={(e) => setAnnualExpenses(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
                <label className="col-span-2 text-sm text-ink-700">{ar ? "الديون الحالية" : "Existing debt"}<input type="number" min="0" value={existingDebt} onChange={(e) => setExistingDebt(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" /></label>
              </div>
              <label className="block text-sm text-ink-700">{ar ? "غرض التمويل" : "Funding purpose"}<textarea value={purpose} onChange={(e) => setPurpose(e.target.value)} rows={2} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" placeholder={ar ? "تجهيز، رأس مال عامل، توسع..." : "Equipment, working capital, expansion..."} /></label>
              <fieldset className="space-y-2 rounded-xl border border-slate-200 p-4"><legend className="px-1 text-sm font-semibold text-ink-700">{ar ? "المستندات المتاحة" : "Available documents"}</legend>
                {[[hasCr,setHasCr,ar?"سجل تجاري":"Commercial registration"],[hasFinancials,setHasFinancials,ar?"قوائم أو توقعات مالية":"Financials or projections"],[hasBankStatements,setHasBankStatements,ar?"كشوف حساب":"Bank statements"],[hasLicense,setHasLicense,ar?"التراخيص المطلوبة":"Required licenses"]].map(([checked,setChecked,label]) => <label key={String(label)} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={checked as boolean} onChange={(e) => (setChecked as (value:boolean)=>void)(e.target.checked)} />{String(label)}</label>)}
              </fieldset>
              <div>
                <label className="block text-sm font-medium text-ink-700">{ar ? "المرحلة" : "Stage"}</label>
                <select value={stage} onChange={(e) => setStage(e.target.value)} className="mt-1 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm focus:border-brand-500 focus:outline-none">
                  <option value="">{ar ? "اختياري" : "Optional"}</option>
                  {stages.map((s) => <option key={s.value} value={s.value}>{ar ? s.ar : s.en}</option>)}
                </select>
              </div>
              <label className="flex items-center gap-3">
                <input type="checkbox" checked={hasMvp} onChange={(e) => setHasMvp(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-brand-600" />
                <span className="text-sm text-ink-700">{ar ? "لدي منتج أولي (MVP)" : "I have an MVP"}</span>
              </label>
              <label className="flex items-center gap-3">
                <input type="checkbox" checked={hasTeam} onChange={(e) => setHasTeam(e.target.checked)} className="h-4 w-4 rounded border-slate-300 text-brand-600" />
                <span className="text-sm text-ink-700">{ar ? "لدي فريق تقني" : "I have a technical team"}</span>
              </label>

              {error && <p className="text-sm text-red-600">{error}</p>}

              <button type="submit" disabled={loading} className="w-full rounded-xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-card hover:bg-brand-700 disabled:opacity-50">
                {loading ? (ar ? "جارٍ البحث..." : "Searching...") : (ar ? "ابحث عن تمويل" : "Find funding")}
              </button>
            </form>

            <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50 p-4">
              <p className="text-xs text-blue-700">
                {ar
                  ? "💡 يمكنك استخدام بيانات مشروعك الحالي لتعبئة الحقول تلقائيًا."
                  : "💡 You can use your existing business profile to auto-fill these fields."}
              </p>
            </div>
            <div className="mt-5 rounded-xl border border-slate-200 p-4">
              <h3 className="text-sm font-bold text-ink-800">{ar ? "خزنة مستندات التمويل" : "Funding document vault"}</h3>
              <p className="mt-1 text-xs text-ink-500">{ar ? "PDF أو Word أو Excel أو صورة — حتى 10MB. التخزين خاص على Cloudflare R2." : "PDF, Word, Excel, or image — up to 10MB. Privately stored on Cloudflare R2."}</p>
              <input aria-label={ar ? "رفع مستند تمويل" : "Upload funding document"} type="file" accept=".pdf,.docx,.xlsx,.jpg,.jpeg,.png" disabled={uploading || !project} onChange={(event) => handleDocument(event.target.files?.[0])} className="mt-3 block w-full text-xs" />
              {!project && <p className="mt-2 text-xs text-amber-700">{ar ? "افتح الأداة من صفحة مشروع لربط المستند به." : "Open this tool from a project to attach documents."}</p>}
              {documents.length > 0 && <ul className="mt-3 space-y-1 text-xs text-ink-700">{documents.map((doc) => <li key={doc.id}>✓ {doc.name} ({Math.ceil((doc.size_bytes || 0) / 1024)} KB)</li>)}</ul>}
            </div>
          </section>

          <section>
            <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card"><div className="flex items-center justify-between"><div><h2 className="font-bold text-ink-900">{ar ? "جاهزية ملف التمويل" : "Funding file readiness"}</h2><p className="mt-1 text-xs text-ink-500">{ar ? "تقييم ذاتي أولي، وليس قرار أهلية رسميًا." : "Initial self-assessment, not an official eligibility decision."}</p></div><strong className="text-3xl text-brand-700">{readinessScore}%</strong></div></div>
            {results === null ? (
              <div className="flex h-full items-center justify-center rounded-2xl border-2 border-dashed border-slate-200 bg-slate-50/50 p-16 text-center">
                <div>
                  <span className="mb-4 block text-5xl opacity-40">🏦</span>
                  <p className="text-sm text-ink-500">{ar ? "أدخل بياناتك لعرض البرامج المتاحة" : "Enter your criteria to see available programs"}</p>
                </div>
              </div>
            ) : results.length === 0 ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-card">
                <p className="text-lg font-bold text-ink-700">{ar ? "لم يتم العثور على برامج مطابقة" : "No matching programs found"}</p>
                <p className="mt-2 text-sm text-ink-500">{ar ? "جرّب تغيير القطاع أو المرحلة." : "Try changing the industry or stage."}</p>
              </div>
            ) : (
              <div className="space-y-4">
                <h2 className="text-lg font-bold text-ink-900">{ar ? `${results.length} برامج مطابقة` : `${results.length} matching programs`}</h2>
                {results.map((r) => (
                  <article key={r.program} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="text-lg font-bold text-ink-900">{ar ? r.name_ar || fundingPrograms[r.program]?.ar || r.name : r.name}</h3>
                        <p className="mt-1 text-sm text-ink-600">{r.program}</p>
                      </div>
                      <div className="text-end">
                        <span className="text-2xl font-bold text-brand-600">{r.score_percent}%</span>
                        <p className="text-xs text-ink-500">{ar ? "نسبة المطابقة" : "Match score"}</p>
                      </div>
                    </div>

                    <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-gradient-to-r from-brand-500 to-brand-400" style={{ width: `${r.score_percent}%` }} />
                    </div>

                    {r.reasons.length > 0 && (
                      <div className="mt-4">
                        <p className="text-xs font-bold text-ink-600">{ar ? "أسباب المطابقة" : "Match reasons"}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {r.reasons.map((reason, i) => <Badge key={i} variant="success">{localizeMatch(reason, ar)}</Badge>)}
                        </div>
                      </div>
                    )}

                    {r.missing.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs font-bold text-ink-600">{ar ? "متطلبات ناقصة" : "Missing requirements"}</p>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {r.missing.map((m, i) => <Badge key={i} variant="warning">{localizeMatch(m, ar)}</Badge>)}
                        </div>
                      </div>
                    )}
                    {ar && r.eligibility_sample_ar?.length > 0 && <div className="mt-4 rounded-xl bg-slate-50 p-4"><p className="text-xs font-bold text-ink-700">عينة شروط أهلية موثقة</p><p className="mt-1 text-xs text-ink-500">{r.provider_role_ar}</p><ul className="mt-2 list-inside list-disc space-y-1 text-xs text-ink-700">{r.eligibility_sample_ar.map((item) => <li key={item}>{item}</li>)}</ul><p className="mt-2 text-[11px] text-ink-500">آخر تحقق: {r.verified_at}</p></div>}
                    {(r.source_url || fundingPrograms[r.program]?.url) && (
                      <a href={r.source_url || fundingPrograms[r.program].url} target="_blank" rel="noreferrer" className="mt-5 inline-flex text-sm font-semibold text-brand-700 hover:underline">
                        {ar ? "زيارة الموقع الرسمي ↗" : "Visit official website ↗"}
                      </a>
                    )}
                  </article>
                ))}

                <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <p className="text-xs text-amber-800">
                    {ar
                      ? "⚠️ النتائج استرشادية ولا تعني الأهلية المضمونة. تحقق من الموقع الرسمي لكل برنامج."
                      : "⚠️ Results are indicative and do not guarantee eligibility. Check each program's official website."}
                  </p>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
