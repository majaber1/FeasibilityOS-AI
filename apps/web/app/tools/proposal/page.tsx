"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import { ServiceHeader } from "@/components/ui/ServiceHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { Stepper } from "@/components/ui/Stepper";
import { Badge } from "@/components/ui/Badge";
import { getToken, listProposals, createProposal, updateProposal, deleteProposal, exportProposal, type Proposal } from "@/lib/api";
import { useProjectContext } from "@/lib/use-project-context";

const proposalTypes = [
  { key: "commercial", icon: "🤝", ar: "عرض تجاري", en: "Commercial Proposal" },
  { key: "technical", icon: "⚙️", ar: "عرض فني", en: "Technical Proposal" },
  { key: "government", icon: "🏛️", ar: "عرض حكومي", en: "Government Proposal" },
  { key: "investor", icon: "💼", ar: "عرض للمستثمرين", en: "Investor Proposal" },
  { key: "consulting", icon: "📋", ar: "عرض استشاري", en: "Consulting Proposal" },
  { key: "partnership", icon: "🤝", ar: "عرض شراكة", en: "Partnership Proposal" },
];

const steps = {
  ar: ["نوع العرض", "العميل / المستلم", "النطاق والحل", "التسعير والجدول", "المراجعة والحفظ"],
  en: ["Proposal type", "Client / recipient", "Scope & solution", "Pricing & timeline", "Review & save"],
};

type ProposalDraft = {
  title: string;
  proposal_type: string;
  client_name: string;
  client_email: string;
  client_company: string;
  scope: string;
  deliverables: string;
  methodology: string;
  price: string;
  currency: string;
  timeline: string;
  validity_days: string;
  terms: string;
};

const emptyDraft: ProposalDraft = {
  title: "",
  proposal_type: "",
  client_name: "",
  client_email: "",
  client_company: "",
  scope: "",
  deliverables: "",
  methodology: "",
  price: "",
  currency: "SAR",
  timeline: "",
  validity_days: "30",
  terms: "",
};

export default function ProposalBuilderPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const [mode, setMode] = useState<"list" | "new">("list");
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [draft, setDraft] = useState<ProposalDraft>(emptyDraft);
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [saving, setSaving] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const [error, setError] = useState("");
  const { project, error: projectError } = useProjectContext();

  useEffect(() => {
    const token = getToken();
    setSignedIn(Boolean(token));
    setAuthChecked(true);
    if (token) listProposals(token).then(setProposals).catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [mode]);

  useEffect(() => {
    if (!project || editingId) return;
    setDraft((current) => ({
      ...current,
      title: current.title || `${ar ? "عرض" : "Proposal"} — ${project.name}`,
      price: current.price || String(project.investment),
    }));
  }, [ar, editingId, project]);

  const set = (field: keyof ProposalDraft, value: string) =>
    setDraft((prev) => ({ ...prev, [field]: value }));

  async function handleSave() {
    const token = getToken();
    if (!token) { setError(ar ? "سجّل الدخول لحفظ العرض." : "Sign in to save the proposal."); return; }
    if (!draft.title.trim() || !draft.client_name.trim() || !draft.scope.trim()) {
      setError(ar ? "أدخل عنوان العرض واسم العميل ونطاق العمل." : "Enter the proposal title, client name, and scope of work.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const proposalPayload = {
        title: draft.title || `${selectedType} proposal`,
        proposal_type: selectedType || "commercial",
        locale: ar ? "ar" : "en",
        payload: {
          project_id: project?.id,
          project_name: project?.name,
          client_name: draft.client_name,
          client_email: draft.client_email,
          client_company: draft.client_company,
          scope: draft.scope,
          deliverables: draft.deliverables,
          methodology: draft.methodology,
          price: draft.price,
          currency: draft.currency,
          timeline: draft.timeline,
          validity_days: draft.validity_days,
          terms: draft.terms,
        },
      };
      if (editingId) {
        await updateProposal(token, editingId, { title: proposalPayload.title, payload: proposalPayload.payload });
      } else {
        await createProposal(token, proposalPayload);
      }
      setMode("list");
      setCurrentStep(0);
      setDraft(emptyDraft);
      setEditingId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  function handleEdit(proposal: Proposal) {
    const payload = proposal.payload || {};
    setEditingId(proposal.id);
    setSelectedType(proposal.proposal_type);
    setDraft({
      ...emptyDraft,
      ...Object.fromEntries(Object.keys(emptyDraft).map((key) => [key, String(payload[key] ?? "")])),
      title: proposal.title,
      proposal_type: proposal.proposal_type,
      currency: String(payload.currency ?? "SAR"),
      validity_days: String(payload.validity_days ?? "30"),
    });
    setCurrentStep(1);
    setMode("new");
    setError("");
  }

  async function handleDelete(proposal: Proposal) {
    const token = getToken();
    if (!token || !window.confirm(ar ? `حذف العرض «${proposal.title}»؟` : `Delete “${proposal.title}”?`)) return;
    setError("");
    try {
      await deleteProposal(token, proposal.id);
      setProposals((current) => current.filter((item) => item.id !== proposal.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleExport(proposal: Proposal, fmt: "pdf" | "docx") {
    const token = getToken(); if (!token) return;
    setError("");
    try { await exportProposal(token, proposal.id, fmt, ar ? "ar" : "en"); }
    catch (err) { setError(err instanceof Error ? err.message : String(err)); }
  }

  if (!authChecked) {
    return <div className="container-page py-20 text-center text-sm text-ink-500">{ar ? "جارٍ التحميل..." : "Loading..."}</div>;
  }

  if (!signedIn) {
    return (
      <div className="container-page py-20 text-center">
        <h1 className="text-2xl font-bold text-ink-900">{ar ? "سجّل الدخول لإنشاء العروض" : "Sign in to create proposals"}</h1>
        <p className="mt-3 text-sm text-ink-600">{ar ? "يتم حفظ العروض في حسابك ويمكن تعديلها أو حذفها لاحقًا." : "Proposals are saved to your account and can be edited or deleted later."}</p>
        <Link href="/login" className="mt-6 inline-flex rounded-xl bg-brand-600 px-6 py-3 text-sm font-bold text-white">{ar ? "تسجيل الدخول" : "Sign in"}</Link>
      </div>
    );
  }

  if (mode === "new") {
    return (
      <div className="min-h-screen bg-[#f5f7f6]">
        <ServiceHeader
          icon="📝"
          title={ar ? "عرض جديد" : "New Proposal"}
          subtitle={ar ? "أنشئ عرضًا احترافيًا خطوة بخطوة" : "Build a professional proposal step by step"}
          breadcrumb={[
            { label: ar ? "الأدوات" : "Tools", href: "/tools" },
            { label: ar ? "منشئ العروض" : "Proposal Builder", href: "/tools/proposal" },
          ]}
        />
        <div className="container-page space-y-8 py-8">
          {project && <div className="rounded-xl border border-brand-200 bg-brand-50 px-5 py-4 text-sm text-brand-800">{ar ? "العرض مرتبط بالمشروع:" : "Proposal linked to project:"} <strong>{project.name}</strong></div>}
          {(error || projectError) && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error || projectError}</p>}
          <Stepper steps={ar ? steps.ar : steps.en} current={currentStep} />

          {currentStep === 0 && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
              <h2 className="text-xl font-bold text-ink-900">{ar ? "اختر نوع العرض" : "Choose proposal type"}</h2>
              <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {proposalTypes.map((pt) => (
                  <button
                    key={pt.key}
                    onClick={() => { setSelectedType(pt.key); setCurrentStep(1); }}
                    className={`group rounded-xl border p-5 text-start transition hover:-translate-y-0.5 hover:shadow-card-hover ${
                      selectedType === pt.key ? "border-brand-500 bg-brand-50" : "border-slate-200 bg-white hover:border-brand-300"
                    }`}
                  >
                    <span className="text-2xl">{pt.icon}</span>
                    <p className="mt-3 font-bold text-ink-900">{ar ? pt.ar : pt.en}</p>
                  </button>
                ))}
              </div>

            </section>
          )}

          {currentStep === 1 && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
              <h2 className="text-xl font-bold text-ink-900">{ar ? "العميل / المستلم" : "Client / Recipient"}</h2>
              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "عنوان العرض" : "Proposal title"}</label>
                  <input value={draft.title} onChange={(e) => set("title", e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" placeholder={ar ? "عنوان العرض" : "Proposal title"} />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "اسم العميل" : "Client name"}</label>
                  <input value={draft.client_name} onChange={(e) => set("client_name", e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "بريد العميل" : "Client email"}</label>
                  <input type="email" value={draft.client_email} onChange={(e) => set("client_email", e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "شركة العميل" : "Client company"}</label>
                  <input value={draft.client_company} onChange={(e) => set("client_company", e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" />
                </div>
              </div>
              <StepNav ar={ar} step={currentStep} setStep={setCurrentStep} />
            </section>
          )}

          {currentStep === 2 && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
              <h2 className="text-xl font-bold text-ink-900">{ar ? "النطاق والحل" : "Scope & Solution"}</h2>
              <div className="mt-6 space-y-5">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "نطاق العمل" : "Scope of work"}</label>
                  <textarea value={draft.scope} onChange={(e) => set("scope", e.target.value)} rows={4} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" placeholder={ar ? "وصف نطاق العمل المقترح..." : "Describe the proposed scope of work..."} />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "المخرجات" : "Deliverables"}</label>
                  <textarea value={draft.deliverables} onChange={(e) => set("deliverables", e.target.value)} rows={3} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" placeholder={ar ? "ما الذي سيتسلمه العميل..." : "What the client will receive..."} />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "المنهجية" : "Methodology"}</label>
                  <textarea value={draft.methodology} onChange={(e) => set("methodology", e.target.value)} rows={3} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" placeholder={ar ? "النهج المقترح لتنفيذ العمل..." : "Proposed approach to executing the work..."} />
                </div>
              </div>
              <StepNav ar={ar} step={currentStep} setStep={setCurrentStep} />
            </section>
          )}

          {currentStep === 3 && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
              <h2 className="text-xl font-bold text-ink-900">{ar ? "التسعير والجدول الزمني" : "Pricing & Timeline"}</h2>
              <div className="mt-6 grid gap-5 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "السعر الإجمالي" : "Total price"}</label>
                  <input type="number" value={draft.price} onChange={(e) => set("price", e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" placeholder="0" />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "العملة" : "Currency"}</label>
                  <select value={draft.currency} onChange={(e) => set("currency", e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none">
                    <option value="SAR">SAR</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "الجدول الزمني" : "Timeline"}</label>
                  <input value={draft.timeline} onChange={(e) => set("timeline", e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" placeholder={ar ? "مثال: 4 أسابيع" : "e.g. 4 weeks"} />
                </div>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "صلاحية العرض (أيام)" : "Validity (days)"}</label>
                  <input type="number" value={draft.validity_days} onChange={(e) => set("validity_days", e.target.value)} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" />
                </div>
                <div className="sm:col-span-2">
                  <label className="mb-1.5 block text-sm font-medium text-ink-700">{ar ? "الشروط والأحكام" : "Terms & conditions"}</label>
                  <textarea value={draft.terms} onChange={(e) => set("terms", e.target.value)} rows={3} className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none" placeholder={ar ? "شروط الدفع، الضمانات..." : "Payment terms, warranties..."} />
                </div>
              </div>
              <StepNav ar={ar} step={currentStep} setStep={setCurrentStep} />
            </section>
          )}

          {currentStep === 4 && (
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
              <h2 className="text-xl font-bold text-ink-900">{ar ? "المراجعة والحفظ" : "Review & Save"}</h2>
              <div className="mt-6 space-y-4">
                <ReviewRow label={ar ? "نوع العرض" : "Type"} value={proposalTypes.find((t) => t.key === selectedType)?.[ar ? "ar" : "en"] || selectedType || "—"} />
                <ReviewRow label={ar ? "العنوان" : "Title"} value={draft.title || "—"} />
                <ReviewRow label={ar ? "العميل" : "Client"} value={draft.client_name || "—"} />
                <ReviewRow label={ar ? "الشركة" : "Company"} value={draft.client_company || "—"} />
                <ReviewRow label={ar ? "النطاق" : "Scope"} value={draft.scope || "—"} />
                <ReviewRow label={ar ? "المخرجات" : "Deliverables"} value={draft.deliverables || "—"} />
                <ReviewRow label={ar ? "السعر" : "Price"} value={draft.price ? `${draft.price} ${draft.currency}` : "—"} />
                <ReviewRow label={ar ? "الجدول الزمني" : "Timeline"} value={draft.timeline || "—"} />
                <ReviewRow label={ar ? "الصلاحية" : "Validity"} value={`${draft.validity_days} ${ar ? "يوم" : "days"}`} />
              </div>
              <div className="mt-6 flex justify-between">
                <button onClick={() => setCurrentStep(3)} className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-ink-700 hover:border-brand-500">{ar ? "السابق" : "Previous"}</button>
                <button onClick={handleSave} disabled={saving} className="rounded-xl bg-gold-500 px-5 py-3 text-sm font-bold text-brand-900 hover:bg-gold-400 disabled:opacity-50">
                  {saving ? (ar ? "جاري الحفظ..." : "Saving...") : (ar ? "حفظ العرض" : "Save proposal")}
                </button>
              </div>
            </section>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <ServiceHeader
        icon="📝"
        title={ar ? "منشئ العروض" : "Proposal Builder"}
        subtitle={ar
          ? "أنشئ عروضًا تجارية احترافية باللغتين العربية والإنجليزية"
          : "Build professional business proposals in Arabic and English"}
        breadcrumb={[{ label: ar ? "الأدوات" : "Tools", href: "/tools" }]}
        actions={
          <button
            onClick={() => setMode("new")}
            className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white shadow-card hover:bg-brand-700"
          >
            {ar ? "عرض جديد" : "New proposal"}
          </button>
        }
      />

      <div className="container-page space-y-8 py-8">
        {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</p>}
        <section className="rounded-2xl border border-brand-200 bg-white p-6 shadow-card sm:p-8">
          <h2 className="text-xl font-bold text-ink-900">{ar ? "أنواع العروض" : "Proposal types"}</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {proposalTypes.map((pt) => (
              <button
                key={pt.key}
                onClick={() => { setSelectedType(pt.key); setMode("new"); setCurrentStep(0); }}
                className="group rounded-xl border border-slate-200 bg-white p-5 text-start transition hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-card-hover"
              >
                <span className="text-2xl">{pt.icon}</span>
                <p className="mt-3 font-bold text-ink-900 group-hover:text-brand-700">{ar ? pt.ar : pt.en}</p>
              </button>
            ))}
          </div>
        </section>

        {proposals.length > 0 ? (
          <section className="rounded-2xl border border-slate-200 bg-white shadow-card">
            <header className="border-b border-slate-100 px-5 py-4">
              <h2 className="font-bold text-ink-900">{ar ? "العروض السابقة" : "Your proposals"}</h2>
            </header>
            <div className="divide-y divide-slate-100">
              {proposals.map((p) => (
                <div key={p.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 hover:bg-slate-50">
                  <div>
                    <p className="font-semibold text-ink-900">{p.title}</p>
                    <p className="mt-1 text-xs text-ink-500">{proposalTypes.find((t) => t.key === p.proposal_type)?.[ar ? "ar" : "en"] || p.proposal_type}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={p.status === "completed" ? "success" : p.status === "draft" ? "neutral" : "info"}>{p.status}</Badge>
                    <button onClick={() => handleExport(p, "pdf")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-bold text-ink-700 hover:bg-slate-50">PDF</button>
                    <button onClick={() => handleExport(p, "docx")} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-bold text-ink-700 hover:bg-slate-50">Word</button>
                    <button onClick={() => handleEdit(p)} className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-bold text-brand-700 hover:bg-brand-50">{ar ? "تعديل" : "Edit"}</button>
                    <button onClick={() => handleDelete(p)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-bold text-red-700 hover:bg-red-50">{ar ? "حذف" : "Delete"}</button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : (
          <EmptyState
            icon="📝"
            title={ar ? "لا توجد عروض سابقة" : "No previous proposals"}
            description={ar ? "ابدأ بإنشاء عرضك التجاري الأول." : "Start by creating your first business proposal."}
            actionLabel={ar ? "عرض جديد" : "New proposal"}
            onAction={() => setMode("new")}
          />
        )}

      </div>
    </div>
  );
}

function StepNav({ ar, step, setStep }: { ar: boolean; step: number; setStep: (s: number) => void }) {
  return (
    <div className="mt-6 flex justify-between">
      <button onClick={() => setStep(Math.max(0, step - 1))} className="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-ink-700 hover:border-brand-500">{ar ? "السابق" : "Previous"}</button>
      <button onClick={() => setStep(step + 1)} className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-semibold text-white hover:bg-brand-700">{ar ? "التالي" : "Next"}</button>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-3 last:border-0">
      <span className="text-sm font-medium text-ink-500">{label}</span>
      <span className="text-end text-sm font-semibold text-ink-900">{value}</span>
    </div>
  );
}
