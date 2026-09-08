"use client";

import { useCallback, useEffect, useState } from "react";
import {
  COLLATERAL_TYPES,
  COLLATERAL_VERIFICATION_STATUSES,
  ENCUMBRANCE_STATUSES,
  createCollateral,
  deleteCollateral,
  getCollateralSummary,
  listCollateral,
  updateCollateral,
  type CollateralItem,
  type CollateralSummary,
  type CollateralType,
  type CollateralVerificationStatus,
  type EncumbranceStatus,
} from "@/lib/api";

const copy = {
  ar: {
    heading: "الضمانات",
    intro: "الضمانات المسجّلة هنا. القيمة المُبلَّغة ليست بالضرورة القيمة القابلة للإقراض، ولا تُفترض أي نسبة خصم من الممول.",
    empty: "لا توجد ضمانات مسجّلة لهذه الدراسة بعد. قد تؤثر الضمانات على جاهزية التمويل والتحقق النهائي من الممول، لكنها لا تضمن الحصول على تمويل.",
    add: "إضافة ضمان",
    cancel: "إلغاء",
    save: "حفظ",
    saving: "جارٍ الحفظ...",
    edit: "تعديل",
    delete: "حذف",
    type: "النوع", description: "الوصف", reportedValue: "القيمة المُبلَّغة (ر.س)",
    verifiedValue: "القيمة الموثّقة (ر.س)", currency: "العملة", valuationDate: "تاريخ التقييم",
    valuationSource: "مصدر التقييم", ownershipStatus: "حالة الملكية",
    encumbranceStatus: "حالة الرهن", encumbranceAmount: "قيمة الرهن (ر.س)", lienHolder: "الجهة الدائنة",
    verificationStatus: "حالة التحقق", notes: "ملاحظات",
    summary: "ملخص الضمانات",
    totalReported: "إجمالي القيمة المُبلَّغة", totalVerified: "القيمة الموثّقة",
    totalEncumbered: "إجمالي المرهون", totalUnencumbered: "إجمالي غير المرهون (من المُبلَّغ)",
    recordCount: "عدد السجلات",
    typeLabels: { PROPERTY: "عقار", EQUIPMENT: "معدات", CASH: "نقد", RECEIVABLES: "ذمم مدينة", GUARANTEE: "ضمان بنكي", OTHER: "أخرى" } as Record<CollateralType, string>,
    verificationLabels: { UNVERIFIED: "غير موثّق", USER_REPORTED: "مُبلَّغ من المستخدم", DOCUMENT_SUPPORTED: "مدعوم بمستند", VERIFIED: "موثّق" } as Record<CollateralVerificationStatus, string>,
    encumbranceLabels: { UNENCUMBERED: "غير مرهون", PARTIALLY_ENCUMBERED: "مرهون جزئيًا", FULLY_ENCUMBERED: "مرهون بالكامل", UNKNOWN: "غير معروف" } as Record<EncumbranceStatus, string>,
  },
  en: {
    heading: "Collateral",
    intro: "Collateral recorded here. The reported value is not necessarily the lendable value, and no lender haircut is assumed.",
    empty: "No collateral has been recorded for this study yet. Collateral may affect funding readiness and the funder's final verification, but it does not guarantee financing.",
    add: "Add collateral",
    cancel: "Cancel",
    save: "Save",
    saving: "Saving...",
    edit: "Edit",
    delete: "Delete",
    type: "Type", description: "Description", reportedValue: "Reported value (SAR)",
    verifiedValue: "Verified value (SAR)", currency: "Currency", valuationDate: "Valuation date",
    valuationSource: "Valuation source", ownershipStatus: "Ownership status",
    encumbranceStatus: "Encumbrance status", encumbranceAmount: "Encumbrance amount (SAR)", lienHolder: "Lien holder",
    verificationStatus: "Verification status", notes: "Notes",
    summary: "Collateral summary",
    totalReported: "Total reported value", totalVerified: "Verified value",
    totalEncumbered: "Total encumbered", totalUnencumbered: "Total unencumbered (of reported)",
    recordCount: "Record count",
    typeLabels: { PROPERTY: "Property", EQUIPMENT: "Equipment", CASH: "Cash", RECEIVABLES: "Receivables", GUARANTEE: "Guarantee", OTHER: "Other" } as Record<CollateralType, string>,
    verificationLabels: { UNVERIFIED: "Unverified", USER_REPORTED: "User-reported", DOCUMENT_SUPPORTED: "Document-supported", VERIFIED: "Verified" } as Record<CollateralVerificationStatus, string>,
    encumbranceLabels: { UNENCUMBERED: "Unencumbered", PARTIALLY_ENCUMBERED: "Partially encumbered", FULLY_ENCUMBERED: "Fully encumbered", UNKNOWN: "Unknown" } as Record<EncumbranceStatus, string>,
  },
};

const VERIFICATION_STYLE: Record<CollateralVerificationStatus, string> = {
  UNVERIFIED: "bg-slate-100 text-slate-600",
  USER_REPORTED: "bg-sky-50 text-sky-800",
  DOCUMENT_SUPPORTED: "bg-amber-50 text-amber-800",
  VERIFIED: "bg-emerald-50 text-emerald-800",
};

const ENCUMBRANCE_STYLE: Record<EncumbranceStatus, string> = {
  UNENCUMBERED: "bg-emerald-50 text-emerald-800",
  PARTIALLY_ENCUMBERED: "bg-amber-50 text-amber-800",
  FULLY_ENCUMBERED: "bg-red-50 text-red-700",
  UNKNOWN: "bg-slate-100 text-slate-600",
};

type Props = { token: string; studyId: number; locale: "ar" | "en"; onChanged?: () => void };

type FormState = {
  collateral_type: CollateralType;
  description: string;
  reported_value: string;
  verified_value: string;
  currency: string;
  valuation_date: string;
  valuation_source: string;
  ownership_status: string;
  encumbrance_status: EncumbranceStatus;
  encumbrance_amount: string;
  lien_holder: string;
  verification_status: CollateralVerificationStatus;
  notes: string;
};

const emptyForm: FormState = {
  collateral_type: "PROPERTY",
  description: "",
  reported_value: "",
  verified_value: "",
  currency: "SAR",
  valuation_date: "",
  valuation_source: "",
  ownership_status: "",
  encumbrance_status: "UNKNOWN",
  encumbrance_amount: "",
  lien_holder: "",
  verification_status: "USER_REPORTED",
  notes: "",
};

function fmt(n: number, locale: "ar" | "en") {
  return new Intl.NumberFormat(locale === "ar" ? "ar-SA" : "en-SA", { maximumFractionDigits: 0 }).format(n);
}

export default function CollateralSection({ token, studyId, locale, onChanged }: Props) {
  const c = copy[locale];

  const [items, setItems] = useState<CollateralItem[] | null>(null);
  const [summary, setSummary] = useState<CollateralSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    try {
      const [itemRows, summaryRow] = await Promise.all([
        listCollateral(token, studyId),
        getCollateralSummary(token, studyId),
      ]);
      setItems(itemRows);
      setSummary(summaryRow);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [token, studyId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  function startAdd() {
    setForm(emptyForm);
    setEditingId(null);
    setShowForm(true);
  }

  function startEdit(item: CollateralItem) {
    setForm({
      collateral_type: item.collateral_type,
      description: item.description,
      reported_value: String(item.reported_value),
      verified_value: item.verified_value !== null ? String(item.verified_value) : "",
      currency: item.currency,
      valuation_date: item.valuation_date ? item.valuation_date.slice(0, 10) : "",
      valuation_source: item.valuation_source ?? "",
      ownership_status: item.ownership_status ?? "",
      encumbrance_status: item.encumbrance_status,
      encumbrance_amount: item.encumbrance_amount !== null ? String(item.encumbrance_amount) : "",
      lien_holder: item.lien_holder ?? "",
      verification_status: item.verification_status,
      notes: item.notes ?? "",
    });
    setEditingId(item.id);
    setShowForm(true);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        collateral_type: form.collateral_type,
        description: form.description.trim(),
        reported_value: Number(form.reported_value),
        verified_value: form.verified_value ? Number(form.verified_value) : undefined,
        currency: form.currency.trim() || "SAR",
        valuation_date: form.valuation_date || undefined,
        valuation_source: form.valuation_source.trim() || undefined,
        ownership_status: form.ownership_status.trim() || undefined,
        encumbrance_status: form.encumbrance_status,
        encumbrance_amount: form.encumbrance_amount ? Number(form.encumbrance_amount) : undefined,
        lien_holder: form.lien_holder.trim() || undefined,
        verification_status: form.verification_status,
        notes: form.notes.trim() || undefined,
      };
      if (editingId !== null) {
        await updateCollateral(token, studyId, editingId, payload);
      } else {
        await createCollateral(token, studyId, payload);
      }
      setShowForm(false);
      setEditingId(null);
      setForm(emptyForm);
      await reload();
      onChanged?.();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(id: number) {
    try {
      await deleteCollateral(token, studyId, id);
      await reload();
      onChanged?.();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }

  const needsEncumbranceAmount = form.encumbrance_status === "PARTIALLY_ENCUMBERED" || form.encumbrance_status === "FULLY_ENCUMBERED";

  return (
    <section id="collateral-section">
      <h3 className="font-semibold text-ink-900">{c.heading}</h3>
      <p className="mt-1 text-sm text-ink-600">{c.intro}</p>
      {error && <p role="alert" className="mt-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {summary && (
        <div className="mt-3 grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <article className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-ink-500">{c.recordCount}</p><p className="mt-1 font-semibold">{summary.record_count}</p></article>
          <article className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-ink-500">{c.totalReported}</p><p className="mt-1 font-semibold">{fmt(summary.total_reported_value, locale)} {locale === "ar" ? "ر.س" : "SAR"}</p></article>
          <article className="rounded-xl bg-emerald-50 p-3"><p className="text-xs text-emerald-700">{c.totalVerified}</p><p className="mt-1 font-semibold text-emerald-900">{fmt(summary.total_verified_value, locale)} {locale === "ar" ? "ر.س" : "SAR"}</p></article>
          <article className="rounded-xl bg-red-50 p-3"><p className="text-xs text-red-700">{c.totalEncumbered}</p><p className="mt-1 font-semibold text-red-900">{fmt(summary.total_encumbered_value, locale)} {locale === "ar" ? "ر.س" : "SAR"}</p></article>
          <article className="rounded-xl bg-brand-50 p-3"><p className="text-xs text-brand-700">{c.totalUnencumbered}</p><p className="mt-1 font-semibold text-brand-900">{fmt(summary.total_unencumbered_reported_value, locale)} {locale === "ar" ? "ر.س" : "SAR"}</p></article>
        </div>
      )}

      <div className="mt-4 flex justify-end">
        <button onClick={showForm ? () => setShowForm(false) : startAdd} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700">
          {showForm ? c.cancel : c.add}
        </button>
      </div>

      {showForm && (
        <form onSubmit={onSubmit} className="mt-4 grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-3">
          <label className="block text-sm">
            <span>{c.type}</span>
            <select value={form.collateral_type} onChange={(e) => setForm({ ...form, collateral_type: e.target.value as CollateralType })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2">
              {COLLATERAL_TYPES.map((t) => <option key={t} value={t}>{c.typeLabels[t]}</option>)}
            </select>
          </label>
          <label className="block text-sm sm:col-span-2">
            <span>{c.description}</span>
            <input required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.reportedValue}</span>
            <input required type="number" min={0} value={form.reported_value} onChange={(e) => setForm({ ...form, reported_value: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.verificationStatus}</span>
            <select value={form.verification_status} onChange={(e) => setForm({ ...form, verification_status: e.target.value as CollateralVerificationStatus })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2">
              {COLLATERAL_VERIFICATION_STATUSES.map((v) => <option key={v} value={v}>{c.verificationLabels[v]}</option>)}
            </select>
          </label>
          {(form.verification_status === "DOCUMENT_SUPPORTED" || form.verification_status === "VERIFIED") && (
            <label className="block text-sm">
              <span>{c.verifiedValue}</span>
              <input type="number" min={0} value={form.verified_value} onChange={(e) => setForm({ ...form, verified_value: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
            </label>
          )}
          <label className="block text-sm">
            <span>{c.valuationDate}</span>
            <input type="date" value={form.valuation_date} onChange={(e) => setForm({ ...form, valuation_date: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.valuationSource}</span>
            <input value={form.valuation_source} onChange={(e) => setForm({ ...form, valuation_source: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <label className="block text-sm">
            <span>{c.encumbranceStatus}</span>
            <select
              value={form.encumbrance_status}
              onChange={(e) => setForm({ ...form, encumbrance_status: e.target.value as EncumbranceStatus, encumbrance_amount: "" })}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            >
              {ENCUMBRANCE_STATUSES.map((s) => <option key={s} value={s}>{c.encumbranceLabels[s]}</option>)}
            </select>
          </label>
          {needsEncumbranceAmount && (
            <label className="block text-sm">
              <span>{c.encumbranceAmount}</span>
              <input required type="number" min={0} value={form.encumbrance_amount} onChange={(e) => setForm({ ...form, encumbrance_amount: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
            </label>
          )}
          {needsEncumbranceAmount && (
            <label className="block text-sm">
              <span>{c.lienHolder}</span>
              <input value={form.lien_holder} onChange={(e) => setForm({ ...form, lien_holder: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
            </label>
          )}
          <label className="block text-sm sm:col-span-3">
            <span>{c.notes}</span>
            <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={2} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
          </label>
          <div className="sm:col-span-3 flex justify-end">
            <button type="submit" disabled={busy} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60">
              {busy ? c.saving : c.save}
            </button>
          </div>
        </form>
      )}

      <div className="mt-4 space-y-3">
        {items === null && <p className="text-sm text-ink-500">…</p>}
        {items !== null && items.length === 0 && !showForm && <p className="text-sm text-ink-500">{c.empty}</p>}
        {items?.map((item) => (
          <article key={item.id} className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-ink-700">{c.typeLabels[item.collateral_type]}</span>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${VERIFICATION_STYLE[item.verification_status]}`}>{c.verificationLabels[item.verification_status]}</span>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${ENCUMBRANCE_STYLE[item.encumbrance_status]}`}>{c.encumbranceLabels[item.encumbrance_status]}</span>
              </div>
              <div className="flex gap-3">
                <button onClick={() => startEdit(item)} className="text-xs font-medium text-brand-700 hover:underline">{c.edit}</button>
                <button onClick={() => onDelete(item.id)} className="text-xs font-medium text-red-600 hover:underline">{c.delete}</button>
              </div>
            </div>
            <h4 className="mt-2 font-semibold text-ink-900">{item.description}</h4>
            <p className="mt-1 text-sm font-medium text-ink-900">
              {c.reportedValue}: {fmt(item.reported_value, locale)} {item.currency}
              {item.verified_value !== null && <> · {c.verifiedValue}: {fmt(item.verified_value, locale)} {item.currency}</>}
              {item.encumbrance_amount !== null && <> · {c.encumbranceAmount}: {fmt(item.encumbrance_amount, locale)} {item.currency}</>}
            </p>
            {item.valuation_date && <p className="mt-1 text-xs text-ink-400">{c.valuationDate}: {item.valuation_date.slice(0, 10)}</p>}
          </article>
        ))}
      </div>
    </section>
  );
}
