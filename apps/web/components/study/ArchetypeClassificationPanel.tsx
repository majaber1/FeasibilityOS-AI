"use client";

import { ARCHETYPE_OPTIONS } from "./archetypeOptions";

type Props = {
  ar: boolean;
  loading: boolean;
  suggested?: string | null;
  selected?: string | null;
  onSelect: (archetype: string) => void;
  onConfirm: () => void;
};

export function ArchetypeClassificationPanel({
  ar,
  loading,
  suggested,
  selected,
  onSelect,
  onConfirm,
}: Props) {
  const value = selected || suggested || null;

  return (
    <section
      className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
      data-testid="archetype-classification-panel"
    >
      <h2 className="text-base font-bold text-ink-900">
        {ar ? "تصنيف نوع المشروع (إلزامي)" : "Project Archetype Classification (required)"}
      </h2>
      <p className="mt-1 text-xs text-ink-500">
        {ar
          ? "أكد نوع المشروع قبل جمع الافتراضات — تختلف الأسئلة حسب النوع."
          : "Confirm the project type before assumptions — questions differ by archetype."}
      </p>
      {suggested ? (
        <p className="mt-2 text-xs text-ink-600" data-testid="archetype-suggestion">
          {ar ? "اقتراح الذكاء الاصطناعي:" : "AI suggestion:"}{" "}
          <span className="font-semibold">{suggested}</span>
        </p>
      ) : null}

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {ARCHETYPE_OPTIONS.map((opt) => {
          const active = value === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              disabled={loading}
              data-testid={`archetype-option-${opt.id}`}
              onClick={() => onSelect(opt.id)}
              className={`rounded-xl border px-3 py-3 text-start text-sm ${
                active
                  ? "border-brand-600 bg-brand-50 text-brand-900"
                  : "border-slate-200 bg-slate-50 text-ink-800 hover:bg-slate-100"
              }`}
            >
              <div className="font-semibold">{ar ? opt.label_ar : opt.label_en}</div>
              <div className="mt-1 text-[11px] text-ink-500">{opt.id}</div>
            </button>
          );
        })}
      </div>

      <button
        type="button"
        disabled={loading || !value}
        onClick={onConfirm}
        data-testid="confirm-archetype-btn"
        className="mt-4 w-full rounded-lg bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
      >
        {loading
          ? ar
            ? "جارٍ التأكيد..."
            : "Confirming..."
          : ar
            ? "تأكيد التصنيف والمتابعة"
            : "Confirm archetype & continue"}
      </button>
    </section>
  );
}
