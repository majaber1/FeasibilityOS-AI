"use client";

import { useEffect, useState } from "react";
import {
  ASSUMPTION_ORIGINS,
  CONFIDENCE_LEVELS,
  createAssumption,
  listAssumptions,
  listEvidence,
  retireAssumption,
  type AssumptionOrigin,
  type ConfidenceLevel,
  type EvidenceItem,
  type StudyAssumption,
} from "@/lib/api";

const copy = {
  ar: {
    intro: "الافتراضات هي قيم يعتمد عليها التحليل المالي. أي افتراض من الذكاء الاصطناعي يجب أن يُعلَّم صراحةً ولا يُعامل كحقيقة سوقية موثّقة.",
    empty: "لا توجد افتراضات محفوظة بعد.",
    add: "إضافة افتراض",
    cancel: "إلغاء",
    save: "حفظ الافتراض",
    saving: "جارٍ الحفظ...",
    retire: "إيقاف",
    key: "المعرّف (بالإنجليزية، بدون مسافات)",
    labelAr: "التسمية بالعربية",
    labelEn: "التسمية بالإنجليزية",
    value: "القيمة",
    unit: "الوحدة",
    origin: "المصدر",
    reason: "السبب",
    confidence: "مستوى الثقة",
    evidence: "الدليل المرتبط",
    none: "بدون",
    version: "الإصدار",
    required: "يرجى تعبئة المعرّف والتسمية والقيمة",
    evidenceRequired: "الافتراض المشتق من دليل يتطلب اختيار دليل مرتبط",
    originLabels: {
      USER: "من المستخدم",
      EVIDENCE_DERIVED: "مشتق من دليل",
      AI_SUGGESTED: "مقترح من الذكاء الاصطناعي",
      DEFAULT: "قيمة افتراضية",
    } as Record<AssumptionOrigin, string>,
    confidenceLabels: { low: "منخفضة", medium: "متوسطة", high: "عالية" } as Record<ConfidenceLevel, string>,
  },
  en: {
    intro: "Assumptions are values the financial analysis relies on. Any AI-suggested assumption must be explicitly labeled and is never treated as a verified market fact.",
    empty: "No assumptions saved yet.",
    add: "Add assumption",
    cancel: "Cancel",
    save: "Save assumption",
    saving: "Saving...",
    retire: "Retire",
    key: "Key (english, no spaces)",
    labelAr: "Arabic label",
    labelEn: "English label",
    value: "Value",
    unit: "Unit",
    origin: "Origin",
    reason: "Reason",
    confidence: "Confidence",
    evidence: "Linked evidence",
    none: "None",
    version: "v",
    required: "Key, label, and value are required",
    evidenceRequired: "Evidence-derived assumptions require a linked evidence item",
    originLabels: {
      USER: "User-provided",
      EVIDENCE_DERIVED: "Evidence-derived",
      AI_SUGGESTED: "AI-suggested",
      DEFAULT: "Default",
    } as Record<AssumptionOrigin, string>,
    confidenceLabels: { low: "Low", medium: "Medium", high: "High" } as Record<ConfidenceLevel, string>,
  },
};

const ORIGIN_STYLE: Record<AssumptionOrigin, string> = {
  USER: "bg-slate-100 text-slate-700",
  EVIDENCE_DERIVED: "bg-emerald-50 text-emerald-800",
  AI_SUGGESTED: "bg-purple-50 text-purple-800",
  DEFAULT: "bg-amber-50 text-amber-800",
};

type Props = { token: string; studyId: number; locale: "ar" | "en" };

const emptyForm = {
  key: "",
  label_en: "",
  label_ar: "",
  value_number: "",
  unit: "",
  origin: "USER" as AssumptionOrigin,
  reason: "",
  confidence: "medium" as ConfidenceLevel,
  evidence_id: "",
};

export default function AssumptionsTab({ token, studyId, locale }: Props) {
  const c = copy[locale];
  const [items, setItems] = useState<StudyAssumption[] | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    listAssumptions(token, studyId)
      .then(setItems)
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)));
    listEvidence(token, studyId).then(setEvidence).catch(() => {});
  }, [token, studyId]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!form.key.trim() || !form.label_en.trim() || !form.label_ar.trim() || !form.value_number.trim()) {
      setFormError(c.required);
      return;
    }
    if (form.origin === "EVIDENCE_DERIVED" && !form.evidence_id) {
      setFormError(c.evidenceRequired);
      return;
    }
    setBusy(true);
    try {
      const created = await createAssumption(token, studyId, {
        key: form.key.trim(),
        label_en: form.label_en.trim(),
        label_ar: form.label_ar.trim(),
        value_number: Number(form.value_number),
        unit: form.unit.trim() || undefined,
        origin: form.origin,
        reason: form.reason.trim() || undefined,
        confidence: form.confidence,
        evidence_id: form.evidence_id ? Number(form.evidence_id) : undefined,
      });
      setItems((prev) => [created, ...(prev ?? []).filter((row) => row.key !== created.key)]);
      setForm(emptyForm);
      setShowForm(false);
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  async function onRetire(id: number) {
    try {
      await retireAssumption(token, studyId, id);
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
        <button onClick={() => setShowForm((v) => !v)} data-testid="add-assumption-btn" className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          {showForm ? c.cancel : c.add}
        </button>
      </div>

      {showForm && (
        <form onSubmit={onSubmit} className="mt-4 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2">
          <label className="block text-sm">
            <span>{c.key}</span>
            <input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} placeholder="monthly_rent" data-testid="assumption-key-input" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.origin}</span>
            <select value={form.origin} onChange={(e) => setForm({ ...form, origin: e.target.value as AssumptionOrigin })} data-testid="assumption-origin-select" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2">
              {ASSUMPTION_ORIGINS.map((o) => (
                <option key={o} value={o}>{c.originLabels[o]}</option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span>{c.labelEn}</span>
            <input value={form.label_en} onChange={(e) => setForm({ ...form, label_en: e.target.value })} data-testid="assumption-label-en" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.labelAr}</span>
            <input value={form.label_ar} onChange={(e) => setForm({ ...form, label_ar: e.target.value })} data-testid="assumption-label-ar" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.value}</span>
            <input type="number" value={form.value_number} onChange={(e) => setForm({ ...form, value_number: e.target.value })} data-testid="assumption-value-input" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
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
          {form.origin === "EVIDENCE_DERIVED" && (
            <label className="block text-sm">
              <span>{c.evidence}</span>
              <select value={form.evidence_id} onChange={(e) => setForm({ ...form, evidence_id: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2">
                <option value="">{c.none}</option>
                {evidence.map((ev) => (
                  <option key={ev.id} value={ev.id}>{ev.title}</option>
                ))}
              </select>
            </label>
          )}
          <label className="block text-sm sm:col-span-2">
            <span>{c.reason}</span>
            <textarea value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} rows={2} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>

          {formError && <p role="alert" className="sm:col-span-2 rounded-md bg-red-50 p-3 text-sm text-red-700">{formError}</p>}

          <div className="sm:col-span-2 flex justify-end">
            <button type="submit" disabled={busy} data-testid="save-assumption-btn" className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60">
              {busy ? c.saving : c.save}
            </button>
          </div>
        </form>
      )}

      <div className="mt-5 space-y-3">
        {items === null && <p className="text-sm text-ink-500">…</p>}
        {items !== null && items.length === 0 && <p className="text-sm text-ink-500">{c.empty}</p>}
        {items?.map((item) => (
          <article key={item.id} data-testid={`assumption-card-${item.key}`} className="flex items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${ORIGIN_STYLE[item.origin]}`}>{c.originLabels[item.origin]}</span>
                <span className="text-xs text-ink-400">{c.version}{item.version}</span>
              </div>
              <h3 className="mt-2 font-semibold text-ink-900">{locale === "ar" ? item.label_ar : item.label_en}</h3>
              <p className="mt-1 text-sm font-medium text-ink-900">
                {item.value_number ?? item.value_text} {item.unit ?? ""}
              </p>
              {item.reason && <p className="mt-1 text-sm text-ink-600">{item.reason}</p>}
            </div>
            <button onClick={() => onRetire(item.id)} className="shrink-0 text-xs font-medium text-red-600 hover:underline">{c.retire}</button>
          </article>
        ))}
      </div>
    </div>
  );
}
