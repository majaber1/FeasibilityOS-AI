"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";
import { getToken, API_BASE } from "@/lib/api";

type Message = {
  role: "user" | "assistant" | "system";
  content: string;
};

type StudyInfo = {
  study_id: string;
  phase: string;
  profile: {
    archetype: string;
    sector: string;
    stage: string;
    decision_goal: string;
    missing_information: string[];
  } | null;
  verdict: string | null;
  decision_rationale: string | null;
  next_action: string | null;
  error: string | null;
};

const PHASE_LABELS: Record<string, { ar: string; en: string }> = {
  DRAFT: { ar: "مسودة", en: "Draft" },
  UNDERSTANDING: { ar: "فهم المشروع", en: "Understanding" },
  NEEDS_INFORMATION: { ar: "جمع المعلومات", en: "Gathering Info" },
  EVIDENCE_REVIEW: { ar: "مراجعة الأدلة", en: "Evidence Review" },
  ASSUMPTIONS_REVIEW: { ar: "مراجعة الافتراضات", en: "Assumptions Review" },
  READY_FOR_ANALYSIS: { ar: "جاهز للتحليل", en: "Ready for Analysis" },
  ANALYZED: { ar: "تم التحليل", en: "Analyzed" },
  DECISION_READY: { ar: "القرار جاهز", en: "Decision Ready" },
  FUNDING_READY: { ar: "جاهز للتمويل", en: "Funding Ready" },
};

const VERDICT_COLORS: Record<string, string> = {
  GO: "bg-emerald-100 text-emerald-800",
  GO_WITH_CONDITIONS: "bg-amber-100 text-amber-800",
  DEFER: "bg-blue-100 text-blue-800",
  NO_GO: "bg-red-100 text-red-800",
  INSUFFICIENT_EVIDENCE: "bg-slate-100 text-slate-800",
};

export default function StudyWorkspacePage() {
  const params = useParams();
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const studyId = params.studyId as string;
  const projectId = params.projectId as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [study, setStudy] = useState<StudyInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const token = getToken();
    if (!token || !studyId || studyId === "new") return;
    fetch(`${API_BASE}/api/v2/studies/${studyId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.study_id) setStudy(data);
      })
      .catch(() => {});
  }, [studyId]);

  async function createStudy(description: string) {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v2/studies`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          project_id: projectId,
          language: locale,
          description,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create study");
      setStudy(data);
      if (data.error) {
        setError(data.error);
        setMessages((prev) => [
          ...prev,
          { role: "system", content: ar ? "تعذر تحليل المشروع. يمكنك إعادة المحاولة." : "The AI could not analyze the project. You can retry." },
        ]);
        return;
      }
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: ar ? "تم إنشاء الدراسة. جارٍ تحليل مشروعك..." : "Study created. Analyzing your project..." },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage() {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setError(null);

    const token = getToken();
    if (!token) {
      setError(ar ? "الرجاء تسجيل الدخول" : "Please sign in");
      setLoading(false);
      return;
    }

    if (!study || studyId === "new") {
      await createStudy(text);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/message`, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text, language: locale }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed");

      setStudy((prev) =>
        prev ? { ...prev, phase: data.phase, profile: data.profile ?? prev.profile, next_action: data.next_action, error: data.error } : prev
      );
      if (data.error) {
        setError(data.error);
        return;
      }

      if (data.response) {
        const cleaned = data.response.replace(/```json[\s\S]*?```/g, "").trim();
        if (cleaned) {
          setMessages((prev) => [...prev, { role: "assistant", content: cleaned }]);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function approveStage(stage: string) {
    if (!study) return;
    const token = getToken();
    if (!token) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/approve/${stage}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ approved: true }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed");
      setStudy((prev) => (prev ? { ...prev, phase: data.phase, next_action: data.next_action } : prev));
      setMessages((prev) => [
        ...prev,
        { role: "system", content: ar ? `تمت الموافقة على مرحلة ${stage}. الانتقال للمرحلة التالية...` : `Approved ${stage} stage. Moving to next phase...` },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const phaseLabel = study?.phase ? (PHASE_LABELS[study.phase]?.[locale] ?? study.phase) : "";

  return (
    <main className="container-page flex h-[calc(100vh-4rem)] flex-col py-4">
      <header className="mb-4 flex items-center justify-between">
        <div>
          <Link href={`/projects`} className="text-sm text-brand-600 hover:underline">
            {ar ? "← المشاريع" : "← Projects"}
          </Link>
          <h1 className="mt-1 text-xl font-bold text-ink-900">
            {ar ? "مساحة عمل الدراسة" : "Study Workspace"}
          </h1>
        </div>
        {study && (
          <div className="flex items-center gap-3">
            <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700">
              {phaseLabel}
            </span>
            {study.verdict && (
              <span className={`rounded-full px-3 py-1 text-xs font-bold ${VERDICT_COLORS[study.verdict] ?? "bg-slate-100"}`}>
                {study.verdict}
              </span>
            )}
          </div>
        )}
      </header>

      {study?.profile && (
        <div className="mb-3 flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">
          <span className="rounded bg-white px-2 py-1 font-medium text-ink-700">{study.profile.archetype}</span>
          <span className="rounded bg-white px-2 py-1 text-ink-600">{study.profile.sector}</span>
          <span className="rounded bg-white px-2 py-1 text-ink-600">{study.profile.stage}</span>
          {study.profile.decision_goal && (
            <span className="rounded bg-white px-2 py-1 text-ink-600">{study.profile.decision_goal}</span>
          )}
        </div>
      )}

      {(study?.phase === "NEEDS_INFORMATION" || study?.phase === "EVIDENCE_REVIEW" || study?.phase === "ASSUMPTIONS_REVIEW") && (
        <div className="mb-3 flex gap-2">
          {study.phase === "NEEDS_INFORMATION" && (
            <button onClick={() => approveStage("profile")} disabled={loading} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">
              {ar ? "تأكيد الملف الشخصي" : "Confirm Profile"}
            </button>
          )}
          {study.phase === "EVIDENCE_REVIEW" && (
            <button onClick={() => approveStage("evidence")} disabled={loading} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">
              {ar ? "الموافقة على الأدلة" : "Approve Evidence"}
            </button>
          )}
          {study.phase === "ASSUMPTIONS_REVIEW" && (
            <button onClick={() => approveStage("assumptions")} disabled={loading} className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">
              {ar ? "الموافقة على الافتراضات" : "Approve Assumptions"}
            </button>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto rounded-xl border border-slate-200 bg-white p-4">
        {messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-center text-ink-400">
            <div>
              <p className="text-lg font-medium">{ar ? "ابدأ بوصف مشروعك" : "Start by describing your project"}</p>
              <p className="mt-2 text-sm">
                {ar
                  ? "اكتب وصفاً لمشروعك وسيقوم المحرك الذكي بتحليله وإرشادك خطوة بخطوة."
                  : "Write a description of your project and the AI engine will analyze it and guide you step by step."}
              </p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`mb-3 flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-brand-600 text-white"
                  : msg.role === "system"
                    ? "bg-amber-50 text-amber-800 border border-amber-200"
                    : "bg-slate-100 text-ink-800"
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="mb-3 flex justify-start">
            <div className="rounded-2xl bg-slate-100 px-4 py-3 text-sm text-ink-500">
              {ar ? "جارٍ التحليل..." : "Analyzing..."}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error && (
        <p className="mt-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage();
        }}
        className="mt-3 flex gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={ar ? "اكتب رسالتك..." : "Type your message..."}
          disabled={loading}
          className="flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition-colors focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded-xl bg-brand-600 px-6 py-3 text-sm font-medium text-white shadow-card transition-colors hover:bg-brand-700 disabled:opacity-50"
        >
          {ar ? "إرسال" : "Send"}
        </button>
      </form>
    </main>
  );
}
