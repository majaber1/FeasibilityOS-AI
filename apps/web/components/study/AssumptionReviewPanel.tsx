"use client";

import { useState } from "react";

export type ReviewAssumption = {
  key: string;
  value: string;
  source?: string;
  confidence?: string;
  low?: string | null;
  base?: string | null;
  high?: string | null;
  ai_estimated?: boolean;
  label_en?: string | null;
  label_ar?: string | null;
  unit?: string | null;
};

type Props = {
  assumptions: ReviewAssumption[];
  ar: boolean;
  loading: boolean;
  onApprove: () => Promise<void>;
  onRegenerate: () => Promise<void>;
  onEdit: (key: string, value: string) => Promise<void>;
};

export function AssumptionReviewPanel({
  assumptions,
  ar,
  loading,
  onApprove,
  onRegenerate,
  onEdit,
}: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  if (!assumptions.length) return null;

  return (
    <section
      className="mb-4 rounded-2xl border border-amber-200 bg-amber-50/40 p-4"
      data-testid="assumption-review-panel"
    >
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-bold text-ink-900">
            {ar ? "مراجعة الافتراضات" : "Assumption review"}
          </h2>
          <p className="mt-1 text-xs text-ink-600">
            {ar
              ? "وافق أو عدّل أو أعد التوليد قبل التحليل المالي."
              : "Approve, edit, or regenerate before financial analysis."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={loading}
            onClick={() => void onRegenerate()}
            data-testid="regenerate-assumptions-btn"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-ink-800 hover:bg-slate-100 disabled:opacity-50"
          >
            {ar ? "إعادة توليد بالذكاء الاصطناعي" : "AI regenerate"}
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => void onApprove()}
            data-testid="approve-assumptions-btn"
            className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {ar ? "موافقة والمتابعة" : "Approve & continue"}
          </button>
        </div>
      </div>

      <ul className="space-y-2">
        {assumptions.map((a) => {
          const label = ar ? a.label_ar || a.key : a.label_en || a.key;
          const ai = Boolean(a.ai_estimated) || (a.source || "").toLowerCase().includes("ai estimated");
          return (
            <li
              key={a.key}
              className="rounded-xl border border-slate-200 bg-white p-3"
              data-testid={`assumption-row-${a.key}`}
              data-ai-estimated={ai ? "true" : "false"}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-ink-900">{label}</p>
                  <p className="text-[11px] text-ink-500">{a.key}{a.unit ? ` · ${a.unit}` : ""}</p>
                </div>
                {ai ? (
                  <span
                    className="rounded bg-violet-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-violet-800"
                    data-testid="ai-estimated-badge"
                  >
                    {ar ? "افتراض مقدّر بالذكاء الاصطناعي" : "AI Estimated Assumption"}
                  </span>
                ) : null}
              </div>

              {editing === a.key ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  <input
                    className="min-w-[12rem] flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    data-testid={`assumption-edit-input-${a.key}`}
                  />
                  <button
                    type="button"
                    disabled={loading}
                    className="rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white"
                    onClick={async () => {
                      await onEdit(a.key, draft);
                      setEditing(null);
                    }}
                  >
                    {ar ? "حفظ" : "Save"}
                  </button>
                  <button
                    type="button"
                    className="rounded-lg border border-slate-300 px-3 py-2 text-xs"
                    onClick={() => setEditing(null)}
                  >
                    {ar ? "إلغاء" : "Cancel"}
                  </button>
                </div>
              ) : (
                <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm text-ink-800">{a.value || "—"}</p>
                  <button
                    type="button"
                    disabled={loading}
                    className="text-xs font-semibold text-brand-700 hover:underline"
                    onClick={() => {
                      setEditing(a.key);
                      setDraft(a.value || "");
                    }}
                    data-testid={`assumption-edit-btn-${a.key}`}
                  >
                    {ar ? "تعديل" : "Edit"}
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
