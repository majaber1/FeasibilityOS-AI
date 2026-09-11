"use client";

import { useEffect, useMemo, useState } from "react";

export type DiscoveryQuestion = {
  id: string;
  prompt?: string;
  question?: string;
  explanation?: string;
  description?: string;
  category?: string;
  answer_type?: string;
  question_type?:
    | "YES_NO"
    | "SINGLE_SELECT"
    | "SELECT"
    | "MULTI_SELECT"
    | "NUMBER"
    | "CURRENCY"
    | "PERCENTAGE"
    | "DATE"
    | "FILE_UPLOAD"
    | "SHORT_TEXT"
    | "LONG_TEXT"
    | "TEXT"
    | string;
  options?: string[];
  required?: boolean;
  allow_ai_estimate?: boolean;
  unit?: string | null;
  field_key?: string | null;
  answer?: string | string[] | number | boolean | null;
  answered?: boolean;
  ai_estimated?: boolean;
};

export type DiscoverySubmitPayload = {
  answers: { id: string; value: unknown }[];
  aiEstimates: string[];
};

type Props = {
  questions: DiscoveryQuestion[];
  ar: boolean;
  loading: boolean;
  onSubmit: (payload: DiscoverySubmitPayload) => Promise<void>;
};

function answerType(q: DiscoveryQuestion): string {
  const raw = (q.answer_type || q.question_type || "TEXT").toUpperCase();
  if (raw === "SINGLE_SELECT") return "SELECT";
  if (raw === "SHORT_TEXT" || raw === "LONG_TEXT") return "TEXT";
  return raw;
}

function isFilled(value: unknown): boolean {
  if (value === null || value === undefined || value === "") return false;
  if (Array.isArray(value) && value.length === 0) return false;
  return true;
}

export function DiscoveryQuestionsPanel({ questions, ar, loading, onSubmit }: Props) {
  const [drafts, setDrafts] = useState<Record<string, unknown>>(() => {
    const init: Record<string, unknown> = {};
    for (const q of questions) {
      if (q.answered && !q.ai_estimated && q.answer != null) init[q.id] = q.answer;
    }
    return init;
  });
  const [aiEstimates, setAiEstimates] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    for (const q of questions) {
      if (q.ai_estimated) init[q.id] = true;
    }
    return init;
  });
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setDrafts((prev) => {
      const next = { ...prev };
      for (const q of questions) {
        if (q.answered && !q.ai_estimated && q.answer != null && next[q.id] === undefined) {
          next[q.id] = q.answer;
        }
      }
      return next;
    });
    setAiEstimates((prev) => {
      const next = { ...prev };
      for (const q of questions) {
        if (q.ai_estimated) next[q.id] = true;
      }
      return next;
    });
  }, [questions]);

  const required = useMemo(
    () => questions.filter((q) => q.required !== false),
    [questions],
  );

  const completedCount = useMemo(() => {
    return required.filter((q) => {
      if (aiEstimates[q.id] || q.ai_estimated) return true;
      if (q.answered && !q.ai_estimated) return true;
      return isFilled(drafts[q.id]);
    }).length;
  }, [required, drafts, aiEstimates]);

  const progressPct = required.length
    ? Math.round((completedCount / required.length) * 100)
    : 100;

  if (!questions.length) return null;

  const safeIndex = Math.min(activeIndex, Math.max(questions.length - 1, 0));
  const current = questions[safeIndex];
  const currentType = answerType(current);
  const currentValue = drafts[current.id];
  const currentAi = Boolean(aiEstimates[current.id]);
  const currentDone =
    currentAi ||
    current.answered ||
    isFilled(currentValue);

  function setValue(id: string, value: unknown) {
    setAiEstimates((prev) => {
      if (!prev[id]) return prev;
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setDrafts((prev) => ({ ...prev, [id]: value }));
  }

  function toggleMulti(id: string, option: string) {
    setAiEstimates((prev) => {
      if (!prev[id]) return prev;
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setDrafts((prev) => {
      const cur = Array.isArray(prev[id]) ? ([...(prev[id] as string[])] as string[]) : [];
      const idx = cur.indexOf(option);
      if (idx >= 0) cur.splice(idx, 1);
      else cur.push(option);
      return { ...prev, [id]: cur };
    });
  }

  function markAiEstimate(id: string) {
    setAiEstimates((prev) => ({ ...prev, [id]: true }));
    setDrafts((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  async function handleSubmit() {
    const answers = questions
      .filter((q) => !aiEstimates[q.id])
      .map((q) => ({ id: q.id, value: drafts[q.id] ?? q.answer ?? null }))
      .filter((a) => isFilled(a.value));
    const estimates = questions.filter((q) => aiEstimates[q.id]).map((q) => q.id);
    await onSubmit({ answers, aiEstimates: estimates });
  }

  const canContinueInterview =
    current.required === false || currentDone || currentAi;

  const title = current.question || current.prompt || current.id;
  const why =
    current.explanation ||
    current.description ||
    (ar
      ? "هذا السؤال يساعد المستشار على فهم اقتصاد مشروعك."
      : "This question helps the advisor understand your business economics.");

  return (
    <section
      className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
      data-testid="discovery-questions-panel"
      data-interview="ai-discovery-advisor"
    >
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-700" data-testid="discovery-interview-eyebrow">
          {ar ? "مستشار اكتشاف الأعمال بالذكاء الاصطناعي" : "AI Business Discovery Advisor"}
        </p>
        <h2 className="mt-1 text-base font-bold text-ink-900" data-testid="discovery-interview-title">
          {ar ? "مقابلة اكتشاف الأعمال" : "AI Discovery Interview"}
        </h2>
        <p className="mt-1 text-xs text-ink-500">
          {ar
            ? "أجب كحوار مع مستشار — أو اطلب من الذكاء الاصطناعي التقدير."
            : "Answer like a consultant interview — or let AI estimate when you are unsure."}
        </p>
      </div>

      <div className="mb-4" data-testid="discovery-progress">
        <div className="mb-1 flex items-center justify-between text-xs text-ink-600">
          <span>
            {ar
              ? `السؤال ${safeIndex + 1} من ${questions.length}`
              : `Question ${safeIndex + 1} of ${questions.length}`}
          </span>
          <span data-testid="discovery-progress-pct">
            {ar ? `${progressPct}% مكتمل` : `${progressPct}% complete`}
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-brand-600 transition-all"
            style={{ width: `${progressPct}%` }}
            data-testid="discovery-progress-bar"
          />
        </div>
        <div className="mt-2 flex flex-wrap gap-1">
          {questions.map((q, idx) => {
            const done =
              aiEstimates[q.id] ||
              q.ai_estimated ||
              q.answered ||
              isFilled(drafts[q.id]);
            return (
              <button
                key={q.id}
                type="button"
                disabled={loading}
                onClick={() => setActiveIndex(idx)}
                title={q.question || q.prompt || q.id}
                data-testid={`discovery-step-${idx}`}
                className={`h-2.5 w-2.5 rounded-full ${
                  idx === safeIndex
                    ? "bg-brand-700 ring-2 ring-brand-200"
                    : done
                      ? "bg-emerald-500"
                      : "bg-slate-300"
                }`}
              />
            );
          })}
        </div>
      </div>

      <article
        className={`rounded-xl border p-4 ${
          currentDone ? "border-emerald-200 bg-emerald-50/40" : "border-slate-200 bg-slate-50"
        }`}
        data-testid={`discovery-question-${current.id}`}
        data-question-type={currentType}
        data-category={current.category || "general"}
        data-ai-estimated={currentAi ? "true" : "false"}
      >
        {current.category ? (
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-ink-500" data-testid="discovery-question-category">
            {current.category.replace(/_/g, " ")}
          </p>
        ) : null}
        <p className="text-sm font-semibold text-ink-900" data-testid="discovery-question-text">
          {title}
          {current.required !== false ? <span className="text-rose-600"> *</span> : null}
        </p>

        <div className="mt-2 rounded-lg border border-sky-100 bg-sky-50/80 px-3 py-2" data-testid="discovery-why-matters">
          <p className="text-[11px] font-semibold text-sky-900">
            {ar ? "لماذا هذا مهم" : "Why this matters"}
          </p>
          <p className="mt-0.5 text-xs text-sky-800">{why}</p>
        </div>

        {!currentAi && currentType === "YES_NO" && (
          <div className="mt-3 flex flex-wrap gap-2" data-testid="discovery-answer-controls">
            {[true, false].map((opt) => {
              const label = opt ? (ar ? "نعم" : "Yes") : ar ? "لا" : "No";
              const selected = currentValue === opt || currentValue === (opt ? "yes" : "no");
              return (
                <button
                  key={String(opt)}
                  type="button"
                  disabled={loading}
                  onClick={() => setValue(current.id, opt)}
                  className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                    selected
                      ? "border-brand-600 bg-brand-600 text-white"
                      : "border-slate-300 bg-white text-ink-800 hover:bg-slate-100"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        )}

        {!currentAi && (currentType === "SELECT" || currentType === "MULTI_SELECT") && (
          <div className="mt-3 flex flex-wrap gap-2" data-testid="discovery-answer-controls">
            {(current.options || []).map((opt) => {
              const selected =
                currentType === "MULTI_SELECT"
                  ? Array.isArray(currentValue) && currentValue.includes(opt)
                  : currentValue === opt;
              return (
                <button
                  key={opt}
                  type="button"
                  disabled={loading}
                  onClick={() =>
                    currentType === "MULTI_SELECT"
                      ? toggleMulti(current.id, opt)
                      : setValue(current.id, opt)
                  }
                  className={`rounded-lg border px-3 py-2 text-sm font-medium ${
                    selected
                      ? "border-brand-600 bg-brand-600 text-white"
                      : "border-slate-300 bg-white text-ink-800 hover:bg-slate-100"
                  }`}
                >
                  {opt}
                </button>
              );
            })}
          </div>
        )}

        {!currentAi &&
          ["NUMBER", "CURRENCY", "PERCENTAGE", "DATE", "TEXT"].includes(currentType) && (
            <div className="mt-3 flex items-center gap-2" data-testid="discovery-answer-controls">
              {currentType === "TEXT" && (current.question_type || "").toUpperCase() === "LONG_TEXT" ? (
                <textarea
                  disabled={loading}
                  value={currentValue == null ? "" : String(currentValue)}
                  onChange={(e) => setValue(current.id, e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                />
              ) : (
                <>
                  <input
                    type={
                      currentType === "DATE"
                        ? "date"
                        : currentType === "TEXT"
                          ? "text"
                          : "number"
                    }
                    disabled={loading}
                    value={currentValue == null ? "" : String(currentValue)}
                    onChange={(e) =>
                      setValue(
                        current.id,
                        currentType === "TEXT" || currentType === "DATE"
                          ? e.target.value
                          : e.target.value === ""
                            ? null
                            : Number(e.target.value),
                      )
                    }
                    className="w-full max-w-md rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                    placeholder={current.unit || ""}
                    data-testid="discovery-answer-input"
                  />
                  {current.unit ? <span className="text-xs text-ink-500">{current.unit}</span> : null}
                </>
              )}
            </div>
          )}

        {currentAi && (
          <div
            className="mt-3 rounded-lg border border-violet-200 bg-violet-50 px-3 py-2 text-xs text-violet-900"
            data-testid="discovery-ai-estimate-badge"
          >
            {ar
              ? "سيتم إنشاء افتراض عبر محرك الافتراضات الحالي (ثقة + مصدر + مبرر) في مراجعة الافتراضات."
              : "An assumption will be created via the existing Assumption Engine (confidence + source + rationale) in Assumption Review."}
          </div>
        )}

        {current.allow_ai_estimate !== false && (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={loading}
              onClick={() => markAiEstimate(current.id)}
              data-testid="discovery-let-ai-estimate"
              className={`rounded-lg border px-3 py-2 text-sm font-semibold ${
                currentAi
                  ? "border-violet-600 bg-violet-600 text-white"
                  : "border-violet-300 bg-white text-violet-800 hover:bg-violet-50"
              }`}
            >
              {ar ? "دع الذكاء الاصطناعي يقدّر" : "Let AI estimate"}
            </button>
            {currentAi ? (
              <button
                type="button"
                disabled={loading}
                onClick={() =>
                  setAiEstimates((prev) => {
                    const next = { ...prev };
                    delete next[current.id];
                    return next;
                  })
                }
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-ink-700"
                data-testid="discovery-clear-ai-estimate"
              >
                {ar ? "سأجيب بنفسي" : "I'll answer myself"}
              </button>
            ) : null}
          </div>
        )}
      </article>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={loading || safeIndex === 0}
          onClick={() => setActiveIndex((i) => Math.max(0, i - 1))}
          className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-ink-800 disabled:opacity-40"
          data-testid="discovery-prev"
        >
          {ar ? "السابق" : "Previous"}
        </button>
        {safeIndex < questions.length - 1 ? (
          <button
            type="button"
            disabled={loading || !canContinueInterview}
            onClick={() => setActiveIndex((i) => Math.min(questions.length - 1, i + 1))}
            className="rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
            data-testid="discovery-next"
          >
            {ar ? "التالي" : "Next"}
          </button>
        ) : (
          <button
            type="button"
            disabled={loading || completedCount < required.length}
            onClick={() => void handleSubmit()}
            data-testid="discovery-questions-submit"
            className="rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {ar ? "حفظ ومتابعة" : "Save & continue"}
          </button>
        )}
        {safeIndex < questions.length - 1 && completedCount >= required.length ? (
          <button
            type="button"
            disabled={loading}
            onClick={() => void handleSubmit()}
            data-testid="discovery-questions-submit-early"
            className="rounded-xl border border-brand-600 bg-white px-4 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-50"
          >
            {ar ? "حفظ ومتابعة الآن" : "Save & continue now"}
          </button>
        ) : null}
      </div>
    </section>
  );
}
