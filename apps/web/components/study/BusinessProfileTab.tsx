"use client";

import { useEffect, useState } from "react";
import { getBusinessProfile, saveBusinessProfile, type BusinessProfile } from "@/lib/api";

const copy = {
  ar: {
    intro: "معلومات المشروع الأساسية. تُستخدم هذه البيانات في التحليل المالي وطلبات التمويل دون الحاجة لإعادة إدخالها.",
    activity: "النشاط التجاري",
    description: "وصف المشروع",
    city: "المدينة",
    region: "المنطقة",
    customerSegment: "العميل المستهدف",
    capacityValue: "الطاقة الاستيعابية",
    capacityUnit: "الوحدة",
    legalEntityType: "الشكل القانوني",
    ownershipNotes: "ملاحظات الملكية",
    isExisting: "شركة قائمة حاليًا؟",
    companyAge: "عمر الشركة (سنوات)",
    currentRevenue: "الإيراد الحالي (ر.س)",
    save: "حفظ الملف",
    saving: "جارٍ الحفظ...",
    saved: "تم الحفظ",
    entityTypes: {
      "": "—",
      sole_proprietorship: "مؤسسة فردية",
      llc: "شركة ذات مسؤولية محدودة",
      joint_stock: "شركة مساهمة",
      other: "أخرى",
    } as Record<string, string>,
  },
  en: {
    intro: "Core business facts. Reused by the financial analysis and funding requests without re-entry.",
    activity: "Business activity",
    description: "Business description",
    city: "City",
    region: "Region",
    customerSegment: "Target customer",
    capacityValue: "Capacity",
    capacityUnit: "Unit",
    legalEntityType: "Legal entity type",
    ownershipNotes: "Ownership notes",
    isExisting: "Existing operating business?",
    companyAge: "Company age (years)",
    currentRevenue: "Current revenue (SAR)",
    save: "Save profile",
    saving: "Saving...",
    saved: "Saved",
    entityTypes: {
      "": "—",
      sole_proprietorship: "Sole proprietorship",
      llc: "LLC",
      joint_stock: "Joint stock company",
      other: "Other",
    } as Record<string, string>,
  },
};

type Props = { token: string; studyId: number; locale: "ar" | "en" };

const empty: Omit<BusinessProfile, "study_id"> = {
  business_activity: "",
  description: "",
  city: "",
  region: "",
  customer_segment: "",
  capacity_value: null,
  capacity_unit: "",
  legal_entity_type: "",
  ownership_notes: "",
  is_existing_business: false,
  company_age_years: null,
  current_revenue: null,
};

export default function BusinessProfileTab({ token, studyId, locale }: Props) {
  const c = copy[locale];
  const [form, setForm] = useState(empty);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    getBusinessProfile(token, studyId)
      .then((profile) => {
        if (profile) {
          const { study_id: _unused, ...rest } = profile;
          setForm({ ...empty, ...rest });
        }
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)))
      .finally(() => setLoading(false));
  }, [token, studyId]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        ...form,
        capacity_value: form.capacity_value === null || Number.isNaN(form.capacity_value) ? undefined : form.capacity_value,
        company_age_years: form.company_age_years === null || Number.isNaN(form.company_age_years) ? undefined : form.company_age_years,
        current_revenue: form.current_revenue === null || Number.isNaN(form.current_revenue) ? undefined : form.current_revenue,
      };
      const saved = await saveBusinessProfile(token, studyId, payload);
      const { study_id: _unused, ...rest } = saved;
      setForm({ ...empty, ...rest });
      setSavedAt(Date.now());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p className="mt-5 text-sm text-ink-500">…</p>;

  return (
    <div className="mt-5">
      <p className="text-sm text-ink-600">{c.intro}</p>
      {error && <p role="alert" className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <form onSubmit={onSubmit} className="mt-4 grid gap-3 sm:grid-cols-2" data-testid="business-profile-form">
        <label className="block text-sm sm:col-span-2">
          <span>{c.activity}</span>
          <input value={form.business_activity ?? ""} onChange={(e) => setForm({ ...form, business_activity: e.target.value })} data-testid="profile-activity-input" className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
        </label>
        <label className="block text-sm sm:col-span-2">
          <span>{c.description}</span>
          <textarea value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
        </label>
        <label className="block text-sm">
          <span>{c.city}</span>
          <input value={form.city ?? ""} onChange={(e) => setForm({ ...form, city: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
        </label>
        <label className="block text-sm">
          <span>{c.region}</span>
          <input value={form.region ?? ""} onChange={(e) => setForm({ ...form, region: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
        </label>
        <label className="block text-sm sm:col-span-2">
          <span>{c.customerSegment}</span>
          <input value={form.customer_segment ?? ""} onChange={(e) => setForm({ ...form, customer_segment: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
        </label>
        <label className="block text-sm">
          <span>{c.capacityValue}</span>
          <input type="number" value={form.capacity_value ?? ""} onChange={(e) => setForm({ ...form, capacity_value: e.target.value ? Number(e.target.value) : null })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
        </label>
        <label className="block text-sm">
          <span>{c.capacityUnit}</span>
          <input value={form.capacity_unit ?? ""} onChange={(e) => setForm({ ...form, capacity_unit: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
        </label>
        <label className="block text-sm">
          <span>{c.legalEntityType}</span>
          <select value={form.legal_entity_type ?? ""} onChange={(e) => setForm({ ...form, legal_entity_type: e.target.value })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2">
            {Object.entries(c.entityTypes).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_existing_business} onChange={(e) => setForm({ ...form, is_existing_business: e.target.checked })} />
          <span>{c.isExisting}</span>
        </label>
        {form.is_existing_business && (
          <>
            <label className="block text-sm">
              <span>{c.companyAge}</span>
              <input type="number" min={0} value={form.company_age_years ?? ""} onChange={(e) => setForm({ ...form, company_age_years: e.target.value ? Number(e.target.value) : null })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
            </label>
            <label className="block text-sm">
              <span>{c.currentRevenue}</span>
              <input type="number" min={0} value={form.current_revenue ?? ""} onChange={(e) => setForm({ ...form, current_revenue: e.target.value ? Number(e.target.value) : null })} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
            </label>
          </>
        )}
        <label className="block text-sm sm:col-span-2">
          <span>{c.ownershipNotes}</span>
          <textarea value={form.ownership_notes ?? ""} onChange={(e) => setForm({ ...form, ownership_notes: e.target.value })} rows={2} className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2" />
        </label>

        <div className="sm:col-span-2 flex items-center justify-end gap-3">
          {savedAt && <span className="text-xs text-emerald-700">{c.saved}</span>}
          <button type="submit" disabled={busy} data-testid="save-business-profile" className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60">
            {busy ? c.saving : c.save}
          </button>
        </div>
      </form>
    </div>
  );
}
