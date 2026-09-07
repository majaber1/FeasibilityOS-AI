"use client";

import { useEffect, useState } from "react";
import {
  CONFIDENCE_LEVELS,
  SOURCE_TYPES,
  VERIFICATION_STATUSES,
  createEvidence,
  deleteEvidence,
  listEvidence,
  type AuthorityLevel,
  type ConfidenceLevel,
  type EvidenceItem,
  type SourceType,
  type VerificationStatus,
} from "@/lib/api";

const copy = {
  ar: {
    intro: "كل رقم أو ادّعاء يُستخدم في التحليل يجب أن يُنسب إلى مصدر هنا، أو يُسجَّل صراحةً كافتراض في تبويب الافتراضات.",
    empty: "لا توجد أدلة محفوظة بعد. أضف أول مصدر لبدء بناء الأساس المرجعي لهذه الدراسة.",
    add: "إضافة دليل",
    cancel: "إلغاء",
    save: "حفظ الدليل",
    saving: "جارٍ الحفظ...",
    delete: "حذف",
    sourceType: "نوع المصدر",
    title: "العنوان",
    claim: "الادّعاء / الحقيقة المذكورة",
    sourceUrl: "رابط المصدر",
    sourceName: "اسم المصدر",
    publisher: "الجهة الناشرة",
    value: "القيمة",
    unit: "الوحدة",
    confidence: "مستوى الثقة",
    verification: "حالة التحقق",
    authority: "مستوى الموثوقية",
    retrieved: "تاريخ الاسترجاع",
    required: "هذا الحقل مطلوب",
    verifiedNeedsUrl: "لا يمكن تعليم دليل بأنه \"موثّق\" دون رابط مصدر.",
    sourceTypeLabels: {
      official_statistic: "إحصاء رسمي",
      regulation: "لائحة/تنظيم",
      funding_program: "برنامج تمويل",
      market_report: "تقرير سوق",
      news: "خبر",
      survey: "استبيان",
      user_document: "مستند من المستخدم",
      ai_inference: "استدلال بالذكاء الاصطناعي",
      other: "أخرى",
    } as Record<SourceType, string>,
    verificationLabels: {
      verified: "موثّق",
      user_provided: "مقدَّم من المستخدم",
      unverified: "غير موثّق",
    } as Record<VerificationStatus, string>,
    confidenceLabels: { low: "منخفضة", medium: "متوسطة", high: "عالية" } as Record<ConfidenceLevel, string>,
  },
  en: {
    intro: "Every number or claim used in the analysis must trace back to a source here, or be explicitly recorded as an assumption in the Assumptions tab.",
    empty: "No evidence saved yet. Add the first source to start this study's evidentiary base.",
    add: "Add evidence",
    cancel: "Cancel",
    save: "Save evidence",
    saving: "Saving...",
    delete: "Delete",
    sourceType: "Source type",
    title: "Title",
    claim: "Claim / stated fact",
    sourceUrl: "Source URL",
    sourceName: "Source name",
    publisher: "Publisher",
    value: "Value",
    unit: "Unit",
    confidence: "Confidence",
    verification: "Verification status",
    authority: "Authority level",
    retrieved: "Retrieved",
    required: "This field is required",
    verifiedNeedsUrl: "Evidence cannot be marked \"verified\" without a source URL.",
    sourceTypeLabels: {
      official_statistic: "Official statistic",
      regulation: "Regulation",
      funding_program: "Funding program",
      market_report: "Market report",
      news: "News",
      survey: "Survey",
      user_document: "User document",
      ai_inference: "AI inference",
      other: "Other",
    } as Record<SourceType, string>,
    verificationLabels: {
      verified: "Verified",
      user_provided: "User-provided",
      unverified: "Unverified",
    } as Record<VerificationStatus, string>,
    confidenceLabels: { low: "Low", medium: "Medium", high: "High" } as Record<ConfidenceLevel, string>,
  },
};

const AUTHORITY_STYLE: Record<AuthorityLevel, string> = {
  OFFICIAL_PRIMARY: "bg-emerald-50 text-emerald-800 border-emerald-200",
  OFFICIAL_SECONDARY: "bg-emerald-50 text-emerald-700 border-emerald-100",
  REGULATOR: "bg-sky-50 text-sky-800 border-sky-200",
  REPUTABLE_INSTITUTION: "bg-sky-50 text-sky-700 border-sky-100",
  COMMERCIAL_SOURCE: "bg-amber-50 text-amber-800 border-amber-200",
  USER_DOCUMENT: "bg-slate-100 text-slate-700 border-slate-200",
  AI_INFERENCE: "bg-purple-50 text-purple-800 border-purple-200",
  UNVERIFIED: "bg-red-50 text-red-700 border-red-200",
};

const VERIFICATION_STYLE: Record<VerificationStatus, string> = {
  verified: "bg-emerald-50 text-emerald-800",
  user_provided: "bg-slate-100 text-slate-700",
  unverified: "bg-red-50 text-red-700",
};

type Props = { token: string; studyId: number; locale: "ar" | "en" };

const emptyForm = {
  source_type: "official_statistic" as SourceType,
  title: "",
  claim: "",
  source_url: "",
  source_name: "",
  publisher: "",
  value_number: "",
  unit: "",
  confidence: "medium" as ConfidenceLevel,
  verification_status: "unverified" as VerificationStatus,
};

export default function EvidenceTab({ token, studyId, locale }: Props) {
  const c = copy[locale];
  const [items, setItems] = useState<EvidenceItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    listEvidence(token, studyId)
      .then(setItems)
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)));
  }, [token, studyId]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!form.title.trim() || !form.claim.trim()) {
      setFormError(c.required);
      return;
    }
    if (form.verification_status === "verified" && !form.source_url.trim()) {
      setFormError(c.verifiedNeedsUrl);
      return;
    }
    setBusy(true);
    try {
      const created = await createEvidence(token, studyId, {
        source_type: form.source_type,
        title: form.title.trim(),
        claim: form.claim.trim(),
        source_url: form.source_url.trim() || undefined,
        source_name: form.source_name.trim() || undefined,
        publisher: form.publisher.trim() || undefined,
        value_number: form.value_number ? Number(form.value_number) : undefined,
        unit: form.unit.trim() || undefined,
        confidence: form.confidence,
        verification_status: form.verification_status,
      });
      setItems((prev) => [created, ...(prev ?? [])]);
      setForm(emptyForm);
      setShowForm(false);
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: number) {
    try {
      await deleteEvidence(token, studyId, id);
      setItems((prev) => (prev ?? []).filter((row) => row.id !== id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }

  return (
    <div className="mt-5">
      <p className="text-sm text-ink-600">{c.intro}</p>
      {error && <p role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <div className="mt-4 flex justify-end">
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          {showForm ? c.cancel : c.add}
        </button>
      </div>

      {showForm && (
        <form onSubmit={onSubmit} className="mt-4 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2">
          <label className="block text-sm sm:col-span-1">
            <span>{c.sourceType}</span>
            <select
              value={form.source_type}
              onChange={(e) => setForm({ ...form, source_type: e.target.value as SourceType })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            >
              {SOURCE_TYPES.map((t) => (
                <option key={t} value={t}>{c.sourceTypeLabels[t]}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm sm:col-span-1">
            <span>{c.verification}</span>
            <select
              value={form.verification_status}
              onChange={(e) => setForm({ ...form, verification_status: e.target.value as VerificationStatus })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            >
              {VERIFICATION_STATUSES.map((v) => (
                <option key={v} value={v}>{c.verificationLabels[v]}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm sm:col-span-2">
            <span>{c.title}</span>
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span>{c.claim}</span>
            <textarea value={form.claim} onChange={(e) => setForm({ ...form, claim: e.target.value })} rows={3} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span>{c.sourceUrl}</span>
            <input value={form.source_url} onChange={(e) => setForm({ ...form, source_url: e.target.value })} placeholder="https://" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.sourceName}</span>
            <input value={form.source_name} onChange={(e) => setForm({ ...form, source_name: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.publisher}</span>
            <input value={form.publisher} onChange={(e) => setForm({ ...form, publisher: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.value}</span>
            <input type="number" value={form.value_number} onChange={(e) => setForm({ ...form, value_number: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.unit}</span>
            <input value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.confidence}</span>
            <select value={form.confidence} onChange={(e) => setForm({ ...form, confidence: e.target.value as ConfidenceLevel })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2">
              {CONFIDENCE_LEVELS.map((v) => (
                <option key={v} value={v}>{c.confidenceLabels[v]}</option>
              ))}
            </select>
          </label>

          {formError && <p role="alert" className="sm:col-span-2 rounded-md bg-red-50 p-3 text-sm text-red-700">{formError}</p>}

          <div className="sm:col-span-2 flex justify-end">
            <button type="submit" disabled={busy} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60">
              {busy ? c.saving : c.save}
            </button>
          </div>
        </form>
      )}

      <div className="mt-5 space-y-3">
        {items === null && <p className="text-sm text-ink-500">…</p>}
        {items !== null && items.length === 0 && <p className="text-sm text-ink-500">{c.empty}</p>}
        {items?.map((item) => (
          <article key={item.id} className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${AUTHORITY_STYLE[item.authority_level]}`}>
                  {item.authority_level.replace(/_/g, " ")}
                </span>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${VERIFICATION_STYLE[item.verification_status]}`}>
                  {c.verificationLabels[item.verification_status]}
                </span>
                <span className="text-xs text-ink-500">{c.sourceTypeLabels[item.source_type]}</span>
              </div>
              <button onClick={() => onDelete(item.id)} className="text-xs font-medium text-red-600 hover:underline">{c.delete}</button>
            </div>
            <h3 className="mt-2 font-semibold text-ink-900">{item.title}</h3>
            <p className="mt-1 text-sm text-ink-700">{item.claim}</p>
            {(item.value_number !== null || item.value_text) && (
              <p className="mt-1 text-sm font-medium text-ink-900">
                {item.value_number ?? item.value_text} {item.unit ?? ""}
              </p>
            )}
            {item.source_url && (
              <a href={item.source_url} target="_blank" rel="noreferrer noopener" className="mt-2 inline-block break-all text-xs text-brand-700 hover:underline">
                {item.source_url}
              </a>
            )}
            <p className="mt-2 text-xs text-ink-400">{c.retrieved}: {new Date(item.retrieved_at).toLocaleDateString(locale === "ar" ? "ar-SA" : "en-SA")}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
