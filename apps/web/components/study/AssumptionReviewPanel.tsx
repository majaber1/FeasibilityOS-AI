"use client";

import { useState } from "react";

export type ReviewAssumption = {
  id?: string | null;
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
  status?: string | null;
  reviewed?: boolean;
};

type Props = {
  assumptions: ReviewAssumption[];
  ar: boolean;
  loading: boolean;
  error?: string | null;
  onApproveAll: () => Promise<void>;
  onRegenerateAll: () => Promise<void>;
  onEdit: (key: string, value: string) => Promise<void>;
  onCardAction: (key: string, action: "approve" | "reject" | "regenerate") => Promise<void>;
};

function statusTone(status?: string | null) {
  switch ((status || "PENDING_REVIEW").toUpperCase()) {
    case "APPROVED":
      return "bg-emerald-100 text-emerald-800 border-emerald-200";
    case "EDITED":
      return "bg-sky-100 text-sky-800 border-sky-200";
    case "REJECTED":
      return "bg-rose-100 text-rose-800 border-rose-200";
    default:
      return "bg-amber-100 text-amber-900 border-amber-200";
  }
}

function sourceLabel(a: ReviewAssumption, ar: boolean) {
  const raw = (a.source || "").toUpperCase();
  if (raw.includes("AI") || a.ai_estimated) {
    return ar ? "مصدر: تقدير ذكاء اصطناعي" : "Source: AI_ESTIMATED";
  }
  if (raw.includes("USER")) {
    return ar ? "مصدر: المستخدم" : "Source: USER_PROVIDED";
  }
  if (raw.includes("RULE")) {
    return ar ? "مصدر: قواعد" : "Source: RULE_BASED";
  }
  return ar ? `مصدر: ${a.source || "غير معروف"}` : `Source: ${a.source || "UNKNOWN"}`;
}

export function AssumptionReviewPanel({
  assumptions,
  ar,
  loading,
  error,
  onApproveAll,
  onRegenerateAll,
  onEdit,
  onCardAction,
}: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [cardBusy, setCardBusy] = useState<string | null>(null);

  const hasAssumptions = assumptions.length > 0;
  const approveDisabled = loading || !hasAssumptions || Boolean(error && !hasAssumptions);

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
              ? "يمكنك اعتماد كل الافتراضات دفعة واحدة، أو اعتماد/تعديل/إعادة توليد كل افتراض على حدة."
              : "Approve all assumptions at once, or approve / edit / regenerate each card individually."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={loading}
            onClick={() => void onRegenerateAll()}
            data-testid="regenerate-assumptions-btn"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-ink-800 hover:bg-slate-100 disabled:opacity-50"
          >
            {ar ? "إعادة توليد الكل" : "Regenerate all"}
          </button>
          <button
            type="button"
            disabled={approveDisabled}
            onClick={() => void onApproveAll()}
            data-testid="approve-assumptions-btn"
            title={
              !hasAssumptions
                ? ar
                  ? "لا توجد افتراضات بعد — أعد التوليد أولاً"
                  : "No assumptions yet — regenerate first"
                : undefined
            }
            className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {ar ? "اعتماد كل الافتراضات" : "Approve All Assumptions"}
          </button>
        </div>
      </div>

      {!hasAssumptions ? (
        <div
          className="rounded-xl border border-dashed border-amber-300 bg-white/80 px-4 py-6 text-center"
          data-testid="assumptions-empty-state"
        >
          <p className="text-sm font-semibold text-ink-800">
            {ar ? "لا توجد افتراضات محفوظة لهذه المرحلة" : "No assumptions saved for this stage"}
          </p>
          <p className="mt-1 text-xs text-ink-600">
            {ar
              ? "حدث خطأ أثناء التوليد أو لم تُحفظ الافتراضات. أعد التوليد للمتابعة."
              : "Generation failed or assumptions were not persisted. Regenerate to continue."}
          </p>
          {error ? <p className="mt-2 text-xs text-rose-700">{error}</p> : null}
          <button
            type="button"
            disabled={loading}
            onClick={() => void onRegenerateAll()}
            className="mt-4 rounded-lg bg-teal-700 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-800 disabled:opacity-50"
          >
            {loading ? (ar ? "جارٍ التوليد…" : "Generating…") : ar ? "إعادة توليد الافتراضات" : "Regenerate assumptions"}
          </button>
        </div>
      ) : (
        <ul className="space-y-2">
          {assumptions.map((a) => {
            const label = ar ? a.label_ar || a.key : a.label_en || a.key;
            const ai = Boolean(a.ai_estimated) || (a.source || "").toUpperCase().includes("AI");
            const status = (a.status || "PENDING_REVIEW").toUpperCase();
            const busy = cardBusy === a.key || loading;
            return (
              <li
                key={a.key}
                className="rounded-xl border border-slate-200 bg-white p-3"
                data-testid={`assumption-row-${a.key}`}
                data-ai-estimated={ai ? "true" : "false"}
                data-status={status}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-ink-900">{label}</p>
                    <p className="text-[11px] text-ink-500">
                      {a.key}
                      {a.unit ? ` · ${a.unit}` : ""}
                      {a.id ? ` · id=${a.id}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${statusTone(status)}`}>
                      {status}
                    </span>
                    <span className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-semibold text-slate-700">
                      {sourceLabel(a, ar)}
                    </span>
                    {a.confidence ? (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                        {a.confidence}
                      </span>
                    ) : null}
                  </div>
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
                      disabled={busy}
                      className="rounded-lg bg-brand-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
                      onClick={async () => {
                        setCardBusy(a.key);
                        try {
                          await onEdit(a.key, draft);
                          setEditing(null);
                        } finally {
                          setCardBusy(null);
                        }
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
                    <div className="flex flex-wrap gap-1.5">
                      <button
                        type="button"
                        disabled={busy}
                        data-testid={`assumption-approve-${a.key}`}
                        className="rounded-lg border border-emerald-300 bg-emerald-50 px-2.5 py-1.5 text-[11px] font-semibold text-emerald-800 hover:bg-emerald-100 disabled:opacity-50"
                        onClick={async () => {
                          setCardBusy(a.key);
                          try {
                            await onCardAction(a.key, "approve");
                          } finally {
                            setCardBusy(null);
                          }
                        }}
                      >
                        {ar ? "اعتماد" : "Approve"}
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        data-testid={`assumption-edit-btn-${a.key}`}
                        className="rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-ink-800 hover:bg-slate-50 disabled:opacity-50"
                        onClick={() => {
                          setEditing(a.key);
                          setDraft(a.value || "");
                        }}
                      >
                        {ar ? "تعديل" : "Edit"}
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        data-testid={`assumption-regenerate-${a.key}`}
                        className="rounded-lg border border-teal-300 bg-teal-50 px-2.5 py-1.5 text-[11px] font-semibold text-teal-800 hover:bg-teal-100 disabled:opacity-50"
                        onClick={async () => {
                          setCardBusy(a.key);
                          try {
                            await onCardAction(a.key, "regenerate");
                          } finally {
                            setCardBusy(null);
                          }
                        }}
                      >
                        {ar ? "إعادة توليد" : "Regenerate"}
                      </button>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default AssumptionReviewPanel;
