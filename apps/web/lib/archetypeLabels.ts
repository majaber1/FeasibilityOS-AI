/**
 * Customer-facing archetype labels.
 * Internal IDs (saas_digital, real_estate, …) must never be shown raw in the UI.
 */

import { ARCHETYPE_OPTIONS } from "@/components/study/archetypeOptions";

const EXTRA_LABELS: Record<string, { en: string; ar: string }> = {
  saas_digital: { en: "SaaS / Digital Platform", ar: "برمجيات / منصة رقمية" },
  saas: { en: "SaaS / Digital Platform", ar: "برمجيات / منصة رقمية" },
  software: { en: "SaaS / Digital Platform", ar: "برمجيات / منصة رقمية" },
  real_estate: { en: "Real Estate Development", ar: "تطوير عقاري" },
  residential: { en: "Real Estate Development", ar: "تطوير عقاري" },
  property: { en: "Real Estate Development", ar: "تطوير عقاري" },
  data_center: { en: "Data Center / Infrastructure", ar: "مركز بيانات / بنية تحتية" },
  datacenter: { en: "Data Center / Infrastructure", ar: "مركز بيانات / بنية تحتية" },
  colocation: { en: "Data Center / Infrastructure", ar: "مركز بيانات / بنية تحتية" },
  professional_services: { en: "Professional Services", ar: "خدمات مهنية" },
  services: { en: "Service Business", ar: "أعمال خدمية" },
  cybersecurity: { en: "Cybersecurity Services", ar: "خدمات الأمن السيبراني" },
  mssp: { en: "Managed Security Services", ar: "خدمات الأمن المُدارة" },
  mobility: { en: "Mobility / Ride-hailing", ar: "التنقل / تطبيقات النقل" },
  industrial: { en: "Industrial / Manufacturing", ar: "صناعي / تصنيع" },
  retail: { en: "Retail / Trading", ar: "تجزئة / تجارة" },
  other: { en: "Other", ar: "أخرى" },
  unknown: { en: "Not classified", ar: "غير مصنّف" },
};

for (const opt of ARCHETYPE_OPTIONS) {
  EXTRA_LABELS[opt.id] = { en: opt.label_en, ar: opt.label_ar };
}

/** True if the string looks like an internal snake_case archetype id. */
export function looksLikeArchetypeId(value: string | null | undefined): boolean {
  if (!value) return false;
  return /^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$/.test(value.trim());
}

export function archetypeLabel(
  id: string | null | undefined,
  locale: "ar" | "en" = "en",
): string {
  if (!id || !String(id).trim()) {
    return locale === "ar" ? "غير مصنّف" : "Not classified";
  }
  const key = String(id).trim().toLowerCase().replace(/[\s-]+/g, "_");
  const hit = EXTRA_LABELS[key];
  if (hit) return locale === "ar" ? hit.ar : hit.en;
  // Never leak snake_case IDs — fall back to a readable title case.
  if (looksLikeArchetypeId(key)) {
    return key
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }
  return String(id).trim();
}
