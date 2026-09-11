"use client";

import { useMemo, useState } from "react";

export type ReviewAssumption = {
  key: string;
  value: string;
  source?: string;
  confidence?: string;
  low?: string | null;
  base?: string | null;
  high?: string | null;
  origin?: string | null;
  ai_estimated?: boolean;
  label_en?: string | null;
  label_ar?: string | null;
  unit?: string | null;
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

function isAiEstimated(a: ReviewAssumption) {
  return Boolean(a.ai_estimated) || (a.source || "").toLowerCase().includes("ai estimated");
}

function isEligible(a: ReviewAssumption) {
  return Boolean(String(a.value || "").trim());
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
  const [whyOpen, setWhyOpen] = useState<string | null>(null);
  const [cardBusy, setCardBusy] = useState<string | null>(null);

  const eligible = useMemo(() => assumptions.filter(isEligible), [assumptions]);
  const invalid = useMemo(() => assumptions.filter((a) => !isEligible(a)), [assumptions]);
  const hasAssumptions = assumptions.length > 0;
  const hasEligible = eligible.length > 0;

  let disableReason: string | null = null;
  if (loading) {
    disableReason = ar ? "جارٍ الحفظ…" : "Saving in progress…";
  } else if (!hasAssumptions) {
    disableReason = ar
      ? "لا توجد افتراضات — هذه مرحلة فارغة. أعد التوليد."
      : "No assumptions generated — regenerate to continue.";
  } else if (!hasEligible) {
    disableReason = ar
      ? "كل الافتراضات فارغة أو غير صالحة — عدّل أو أعد التوليد."
      : "All assumptions are empty/invalid — edit or regenerate.";
  } else if (error && !hasAssumptions) {
    disableReason = error;
  }

  const approveDisabled = Boolean(disableReason);

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
              ? "راجع كل افتراض: اعتماد / تعديل / رفض / إعادة توليد. ثم اعتمد كل الافتراضات المؤهلة للمتابعة."
              : "Review each assumption: Approve / Edit / Reject / Regenerate. Then approve all eligible assumptions to continue."}
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
            data-testid="approve-all-eligible-assumptions-btn"
            title={disableReason || undefined}
            className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {ar ? "اعتماد كل الافتراضات المؤهلة" : "Approve all eligible assumptions"}
          </button>
        </div>
      </div>

      {disableReason ? (
        <p
          className="mb-3 rounded-lg border border-amber-300 bg-amber-100/70 px-3 py-2 text-xs text-amber-950"
          data-testid="approve-disabled-reason"
          role="status"
        >
          {disableReason}
        </p>
      ) : null}

      {invalid.length > 0 ? (
        <p
          className="mb-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800"
          data-testid="invalid-assumptions-banner"
        >
          {ar
            ? `${invalid.length} افتراض غير صالح يمنع الاعتماد الجماعي حتى يُعدَّل أو يُعاد توليده: ${invalid.map((a) => a.key).join(", ")}`
            : `${invalid.length} invalid assumption(s) block bulk approval until edited or regenerated: ${invalid.map((a) => a.key).join(", ")}`}
        </p>
      ) : null}

      {!hasAssumptions ? (
        <div
          className="rounded-xl border border-dashed border-amber-300 bg-white/80 px-4 py-6 text-center"
          data-testid="assumptions-empty-state"
        >
          <p className="text-sm font-semibold text-ink-800">
            {ar ? "مرحلة مراجعة الافتراضات بلا صفوف محفوظة" : "Assumptions review phase has no saved rows"}
          </p>
          <p className="mt-1 text-xs text-ink-600">
            {ar
              ? "هذا خلل في توليد/انتقال المرحلة — أعد التوليد لإصلاح الحالة."
              : "This is a generation/transition defect — regenerate to repair the state."}
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
            const ai = isAiEstimated(a);
            const eligibleRow = isEligible(a);
            const busy = cardBusy === a.key || loading;
            return (
              <li
                key={a.key}
                className="rounded-xl border border-slate-200 bg-white p-3"
                data-testid={`assumption-row-${a.key}`}
                data-ai-estimated={ai ? "true" : "false"}
                data-eligible={eligibleRow ? "true" : "false"}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-ink-900">{label}</p>
                    <p className="text-[11px] text-ink-500">
                      {a.key}
                      {a.unit ? ` · ${a.unit}` : ""}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {ai ? (
                      <span
                        className="rounded bg-violet-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-violet-800"
                        data-testid="ai-estimated-badge"
                      >
                        {ar ? "افتراض مقدّر بالذكاء الاصطناعي" : "AI Estimated Assumption"}
                      </span>
                    ) : (
                      <span className="rounded bg-emerald-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-emerald-800">
                        {ar ? "مؤكد من المستخدم" : "User confirmed"}
                      </span>
                    )}
                    {!eligibleRow ? (
                      <span className="rounded bg-rose-100 px-2 py-1 text-[10px] font-bold uppercase text-rose-800">
                        {ar ? "غير صالح" : "Invalid"}
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
                        data-testid={`assumption-reject-${a.key}`}
                        className="rounded-lg border border-rose-300 bg-rose-50 px-2.5 py-1.5 text-[11px] font-semibold text-rose-800 hover:bg-rose-100 disabled:opacity-50"
                        onClick={async () => {
                          setCardBusy(a.key);
                          try {
                            await onCardAction(a.key, "reject");
                          } finally {
                            setCardBusy(null);
                          }
                        }}
                      >
                        {ar ? "رفض" : "Reject"}
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
                      <button
                        type="button"
                        data-testid={`assumption-why-${a.key}`}
                        className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-[11px] font-semibold text-slate-700 hover:bg-slate-100"
                        onClick={() => setWhyOpen(whyOpen === a.key ? null : a.key)}
                      >
                        {ar ? "لماذا؟" : "Why"}
                      </button>
                    </div>
                  </div>
                )}

                {whyOpen === a.key ? (
                  <div
                    className="mt-2 rounded-lg bg-slate-50 px-3 py-2 text-[11px] text-ink-700"
                    data-testid={`assumption-why-panel-${a.key}`}
                  >
                    <p>
                      <span className="font-semibold">{ar ? "المصدر:" : "Source:"}</span> {a.source || "—"}
                    </p>
                    <p>
                      <span className="font-semibold">{ar ? "الأصل:" : "Origin:"}</span> {a.origin || "—"}
                    </p>
                    <p>
                      <span className="font-semibold">{ar ? "الثقة:" : "Confidence:"}</span> {a.confidence || "—"}
                    </p>
                    {(a.low || a.base || a.high) && (
                      <p>
                        L/B/H: {a.low ?? "—"} / {a.base ?? "—"} / {a.high ?? "—"}
                      </p>
                    )}
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default AssumptionReviewPanel;
