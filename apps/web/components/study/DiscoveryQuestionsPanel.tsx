"use client";

import { useState } from "react";

export type DiscoveryQuestion = {
  id: string;
  prompt: string;
  question_type:
    | "YES_NO"
    | "SINGLE_SELECT"
    | "MULTI_SELECT"
    | "NUMBER"
    | "CURRENCY"
    | "PERCENTAGE"
    | "DATE"
    | "FILE_UPLOAD"
    | "SHORT_TEXT"
    | "LONG_TEXT"
    | string;
  options?: string[];
  required?: boolean;
  unit?: string | null;
  field_key?: string | null;
  answer?: string | string[] | number | boolean | null;
  answered?: boolean;
};

type Props = {
  questions: DiscoveryQuestion[];
  ar: boolean;
  loading: boolean;
  onSubmit: (answers: { id: string; value: unknown }[]) => Promise<void>;
};

export function DiscoveryQuestionsPanel({ questions, ar, loading, onSubmit }: Props) {
  const [drafts, setDrafts] = useState<Record<string, unknown>>(() => {
    const init: Record<string, unknown> = {};
    for (const q of questions) {
      if (q.answered && q.answer != null) init[q.id] = q.answer;
    }
    return init;
  });

  const unanswered = questions.filter((q) => q.required !== false && !q.answered);
  if (!questions.length) return null;

  function setValue(id: string, value: unknown) {
    setDrafts((prev) => ({ ...prev, [id]: value }));
  }

  function toggleMulti(id: string, option: string) {
    setDrafts((prev) => {
      const cur = Array.isArray(prev[id]) ? ([...(prev[id] as string[])] as string[]) : [];
      const idx = cur.indexOf(option);
      if (idx >= 0) cur.splice(idx, 1);
      else cur.push(option);
      return { ...prev, [id]: cur };
    });
  }

  async function handleSubmit() {
    const answers = questions
      .map((q) => ({ id: q.id, value: drafts[q.id] ?? q.answer ?? null }))
      .filter((a) => a.value !== null && a.value !== undefined && a.value !== "");
    await onSubmit(answers);
  }

  return (
    <section
      className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
      data-testid="discovery-questions-panel"
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-ink-900">
            {ar ? "أسئلة منظمة لاستكمال الملف" : "Structured questions to complete the profile"}
          </h2>
          <p className="mt-1 text-xs text-ink-500">
            {ar
              ? `${unanswered.length} سؤال مطلوب متبقٍ — اختر من الخيارات بدل كتابة فقرات.`
              : `${unanswered.length} required remaining — choose options instead of writing paragraphs.`}
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {questions.map((q) => {
          const value = drafts[q.id];
          const done = q.answered || (value !== undefined && value !== null && value !== "");
          return (
            <div
              key={q.id}
              className={`rounded-xl border p-3 ${done ? "border-emerald-200 bg-emerald-50/40" : "border-slate-200 bg-slate-50"}`}
              data-testid={`discovery-question-${q.id}`}
              data-question-type={q.question_type}
            >
              <p className="text-sm font-semibold text-ink-900">
                {q.prompt}
                {q.required !== false ? <span className="text-rose-600"> *</span> : null}
              </p>

              {q.question_type === "YES_NO" && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {[true, false].map((opt) => {
                    const label = opt ? (ar ? "نعم" : "Yes") : ar ? "لا" : "No";
                    const selected = value === opt || value === (opt ? "yes" : "no");
                    return (
                      <button
                        key={String(opt)}
                        type="button"
                        disabled={loading}
                        onClick={() => setValue(q.id, opt)}
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

              {(q.question_type === "SINGLE_SELECT" || q.question_type === "MULTI_SELECT") && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {(q.options || []).map((opt) => {
                    const selected =
                      q.question_type === "MULTI_SELECT"
                        ? Array.isArray(value) && value.includes(opt)
                        : value === opt;
                    return (
                      <button
                        key={opt}
                        type="button"
                        disabled={loading}
                        onClick={() =>
                          q.question_type === "MULTI_SELECT"
                            ? toggleMulti(q.id, opt)
                            : setValue(q.id, opt)
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

              {["NUMBER", "CURRENCY", "PERCENTAGE", "DATE", "SHORT_TEXT"].includes(q.question_type) && (
                <div className="mt-2 flex items-center gap-2">
                  <input
                    type={
                      q.question_type === "DATE"
                        ? "date"
                        : q.question_type === "SHORT_TEXT"
                          ? "text"
                          : "number"
                    }
                    disabled={loading}
                    value={value == null ? "" : String(value)}
                    onChange={(e) =>
                      setValue(
                        q.id,
                        q.question_type === "SHORT_TEXT" || q.question_type === "DATE"
                          ? e.target.value
                          : e.target.value === ""
                            ? null
                            : Number(e.target.value),
                      )
                    }
                    className="w-full max-w-md rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                    placeholder={q.unit || ""}
                  />
                  {q.unit ? <span className="text-xs text-ink-500">{q.unit}</span> : null}
                </div>
              )}

              {q.question_type === "LONG_TEXT" && (
                <textarea
                  disabled={loading}
                  value={value == null ? "" : String(value)}
                  onChange={(e) => setValue(q.id, e.target.value)}
                  rows={3}
                  className="mt-2 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                />
              )}

              {q.question_type === "FILE_UPLOAD" && (
                <p className="mt-2 text-xs text-ink-500">
                  {ar
                    ? "ارفع المستند لاحقاً من المحادثة أو المرفقات عند التوفر."
                    : "Upload the document later via chat/attachments when available."}
                </p>
              )}
            </div>
          );
        })}
      </div>

      <button
        type="button"
        disabled={loading}
        onClick={() => void handleSubmit()}
        data-testid="discovery-questions-submit"
        className="mt-4 rounded-xl bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {ar ? "حفظ الإجابات" : "Save answers"}
      </button>
    </section>
  );
}
