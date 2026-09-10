"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";
import { getToken, API_BASE } from "@/lib/api";
import { DiscoveryQuestionsPanel, type DiscoveryQuestion } from "@/components/study/DiscoveryQuestionsPanel";

type Message = {
  role: "user" | "assistant" | "system";
  content: string;
};

type Claim = {
  statement: string;
  source_type?: string;
  confidence?: number;
  source_url?: string | null;
  source_title?: string | null;
  status?: "draft" | "approved" | "rejected" | string;
};

type Assumption = {
  key: string;
  value: string;
  source?: string;
  confidence?: string;
  low?: string | null;
  base?: string | null;
  high?: string | null;
  origin?: "user" | "evidence_derived" | "provisional_estimate" | string;
  status?: "draft" | "approved" | "rejected" | string;
  rationale?: string | null;
};

type StudyInfo = {
  study_id: string;
  phase: string;
  profile: {
    archetype: string;
    sector: string;
    stage: string;
    decision_goal: string;
    missing_information?: string[];
    structured_answers?: Record<string, unknown>;
  } | null;
  gate_choice?: "manual" | "research" | "provisional" | string | null;
  evidence_status?: "not_started" | "empty" | "degraded" | "available" | string | null;
  blocking_reason?: string | null;
  claims?: Claim[];
  assumptions?: Assumption[];
  discovery_questions?: DiscoveryQuestion[];
  financial_results?: Record<string, unknown> | null;
  decision_risks?: string[];
  decision_conditions?: string[];
  decision_rationale?: string | null;
  verdict?: string | null;
  claims_count?: number;
  assumptions_count?: number;
  messages?: Message[];
  response?: string;
  error?: string | null;
  next_action?: string | null;
  workflow_meta?: Record<string, unknown> | null;
};

type ItemAction =
  | "edit"
  | "approve"
  | "reject"
  | "ask_why"
  | "request_alternative"
  | "regenerate";

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
  NEED_MORE_VALIDATION: "bg-orange-100 text-orange-800",
  DEFER: "bg-blue-100 text-blue-800",
  NO_GO: "bg-red-100 text-red-800",
  INSUFFICIENT_EVIDENCE: "bg-slate-100 text-slate-800",
};

const ORIGIN_LABELS: Record<string, { ar: string; en: string }> = {
  provisional_estimate: { ar: "تقدير مؤقت", en: "Provisional estimate" },
  evidence_derived: { ar: "مستنتج من الأدلة", en: "Evidence-derived" },
  user: { ar: "من المستخدم", en: "User-provided" },
  platform_derived: { ar: "مشتق من المنصة", en: "Platform-derived" },
};

function stripJsonFences(text: string): string {
  return text.replace(/```json[\s\S]*?```/g, "").trim();
}

/** Session auth uses an HTTP-only cookie; never send Authorization: Bearer session. */
function studyFetchHeaders(token: string): HeadersInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token && token !== "session") {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

/** Client-side guard: AI estimates must never appear as Evidence. */
function isEvidenceClaim(claim: Claim): boolean {
  const sourceType = claim.source_type;
  if (!sourceType || sourceType === "ai_assumption") return false;
  if (!claim.statement?.trim()) return false;
  return ["official", "user_input", "document", "unverified"].includes(sourceType);
}

function applyStudyPayload(
  data: StudyInfo,
  setStudy: (s: StudyInfo) => void,
  setMessages: (msgs: Message[] | ((prev: Message[]) => Message[])) => void,
  opts?: { mergeAssistantStub?: string; replaceMessages?: boolean },
) {
  const filteredClaims = (data.claims || []).filter(isEvidenceClaim);
  setStudy({
    ...data,
    claims: filteredClaims,
    claims_count: filteredClaims.length,
  });
  const hydrated = (data.messages || [])
    .map((m) => ({
      role: m.role,
      content: m.role === "assistant" ? stripJsonFences(m.content) : m.content,
    }))
    .filter((m) => m.content);

  if (opts?.replaceMessages !== false) {
    if (hydrated.length > 0) {
      setMessages(hydrated);
    } else if (opts?.mergeAssistantStub) {
      setMessages([{ role: "assistant", content: opts.mergeAssistantStub }]);
    }
  }
}

function EvidenceStatusBanner({
  status,
  ar,
  blockingReason,
}: {
  status?: string | null;
  ar: boolean;
  blockingReason?: string | null;
}) {
  if (!status || status === "not_started") return null;

  if (status === "empty") {
    return (
      <div
        data-testid="evidence-status"
        data-status="empty"
        className="mb-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] text-slate-700"
      >
        {ar
          ? "حالة الأدلة: فارغة — لم يُعثر على أدلة مدعومة بمصادر."
          : "Evidence status: empty — no source-backed evidence found."}
      </div>
    );
  }

  if (status === "degraded") {
    return (
      <div
        data-testid="evidence-status"
        data-status="degraded"
        className="mb-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-900"
      >
        {ar
          ? "حالة الأدلة: متدهورة — البحث عن المصادر لم يكتمل أو فشل جزئياً."
          : "Evidence status: degraded — source research incomplete or partially failed."}
        {blockingReason ? ` (${blockingReason})` : ""}
      </div>
    );
  }

  if (status === "available") {
    return (
      <div
        data-testid="evidence-status"
        data-status="available"
        className="mb-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-[11px] text-emerald-900"
      >
        {ar
          ? "حالة الأدلة: متاحة — توجد أدلة مدعومة بمصادر للمراجعة."
          : "Evidence status: available — source-backed evidence is ready for review."}
      </div>
    );
  }

  return (
    <div
      data-testid="evidence-status"
      data-status={status}
      className="mb-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] text-slate-700"
    >
      {ar ? `حالة الأدلة: ${status}` : `Evidence status: ${status}`}
    </div>
  );
}

function ItemActionBar({
  ar,
  loading,
  showRegenerate,
  onAction,
}: {
  ar: boolean;
  loading: boolean;
  showRegenerate: boolean;
  onAction: (action: ItemAction) => void;
}) {
  const btn =
    "rounded border border-slate-200 bg-white px-1.5 py-0.5 text-[10px] font-medium text-ink-700 hover:bg-slate-50 disabled:opacity-50";
  return (
    <div className="mt-2 flex flex-wrap gap-1">
      <button type="button" className={btn} disabled={loading} onClick={() => onAction("edit")}>
        {ar ? "تعديل" : "Edit"}
      </button>
      <button type="button" className={btn} disabled={loading} onClick={() => onAction("approve")}>
        {ar ? "موافقة" : "Approve"}
      </button>
      <button type="button" className={btn} disabled={loading} onClick={() => onAction("reject")}>
        {ar ? "رفض" : "Reject"}
      </button>
      <button type="button" className={btn} disabled={loading} onClick={() => onAction("ask_why")}>
        {ar ? "لماذا؟" : "Ask Why"}
      </button>
      <button
        type="button"
        className={btn}
        disabled={loading}
        onClick={() => onAction("request_alternative")}
      >
        {ar ? "بديل" : "Request Alternative"}
      </button>
      {showRegenerate && (
        <button
          type="button"
          className={btn}
          disabled={loading}
          onClick={() => onAction("regenerate")}
        >
          {ar ? "إعادة توليد" : "Regenerate"}
        </button>
      )}
    </div>
  );
}

export default function StudyWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const studyId = params.studyId as string;
  const projectId = params.projectId as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [hydrating, setHydrating] = useState(studyId !== "new");
  const [study, setStudy] = useState<StudyInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const filledPanelsRef = useRef<HTMLDivElement>(null);

  const claims = (study?.claims || []).filter(isEvidenceClaim);
  const assumptions = study?.assumptions || [];
  const financial = study?.financial_results || null;
  const missing = study?.profile?.missing_information || [];
  const evidenceStatus = study?.evidence_status || null;
  const showFilledPanels =
    !!study &&
    (claims.length > 0 ||
      assumptions.length > 0 ||
      !!financial ||
      !!study.verdict ||
      !!study.decision_rationale ||
      evidenceStatus === "empty" ||
      evidenceStatus === "degraded" ||
      evidenceStatus === "available" ||
      study.phase === "EVIDENCE_REVIEW" ||
      study.phase === "ASSUMPTIONS_REVIEW" ||
      study.phase === "READY_FOR_ANALYSIS" ||
      study.phase === "ANALYZED" ||
      study.phase === "DECISION_READY" ||
      study.phase === "FUNDING_READY");

  useEffect(() => {
    if ((study?.claims_count || 0) > 0 || (study?.assumptions_count || 0) > 0 || showFilledPanels) {
      filledPanelsRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, study?.claims_count, study?.assumptions_count, showFilledPanels]);

  useEffect(() => {
    const token = getToken();
    if (!token || !studyId || studyId === "new") {
      setHydrating(false);
      return;
    }
    setHydrating(true);
    fetch(`${API_BASE}/api/v2/studies/${studyId}`, {
      credentials: "same-origin",
      headers: studyFetchHeaders(token),
    })
      .then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || "Failed to load study");
        return data as StudyInfo;
      })
      .then((data) => {
        if (data.study_id) {
          applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
          if (data.error) setError(data.error);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setHydrating(false));
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
        headers: studyFetchHeaders(token),
        body: JSON.stringify({
          project_id: projectId,
          language: locale,
          description,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to create study");

      applyStudyPayload(data, setStudy, setMessages, {
        replaceMessages: true,
        mergeAssistantStub: ar
          ? "تم إنشاء الدراسة. جارٍ تحليل مشروعك..."
          : "Study created. Analyzing your project...",
      });

      if (data.response) {
        const cleaned = stripJsonFences(data.response);
        if (cleaned) {
          setMessages((prev) => {
            const has = prev.some((m) => m.role === "assistant" && m.content === cleaned);
            return has ? prev : [...prev, { role: "assistant", content: cleaned }];
          });
        }
      }

      if (data.error) {
        setError(data.error);
        return;
      }

      if (data.study_id) {
        router.replace(`/projects/${projectId}/studies/${data.study_id}/workspace`);
      }
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
        headers: studyFetchHeaders(token),
        body: JSON.stringify({ message: text, language: locale }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed");

      setStudy((prev) =>
        prev
          ? {
              ...prev,
              ...data,
              study_id: data.study_id || prev.study_id,
              claims: (data.claims || []).filter(isEvidenceClaim),
            }
          : data,
      );

      if (data.messages?.length) {
        applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
      } else if (data.response) {
        const cleaned = stripJsonFences(data.response);
        if (cleaned) {
          setMessages((prev) => [...prev, { role: "assistant", content: cleaned }]);
        }
      }

      if (data.error) {
        setError(data.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function submitInformationGate(choice: "manual" | "research" | "provisional") {
    if (!study || loading) return;
    const token = getToken();
    if (!token) {
      setError(ar ? "الرجاء تسجيل الدخول" : "Please sign in");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/information-gate`, {
        method: "POST",
        credentials: "same-origin",
        headers: studyFetchHeaders(token),
        body: JSON.stringify({ choice }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        const message = Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
          : detail || "Failed";
        throw new Error(message);
      }
      applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
      const systemNote =
        choice === "manual"
          ? ar
            ? "اخترت إكمال المعلومات بنفسك. أكمل النواقص في المحادثة."
            : "You chose to complete missing information yourself. Continue in chat."
          : choice === "research"
            ? ar
              ? "جارٍ إنشاء مسودة دراسة بالذكاء الاصطناعي — بحث عن أدلة مدعومة بمصادر..."
              : "Generating AI Study Draft — researching source-backed evidence..."
            : ar
              ? "جارٍ إنشاء دراسة تقديرية — التقديرات تُحفظ كافتراضات فقط."
              : "Creating a provisional study — estimates are Assumptions only.";
      setMessages((prev) => [...prev, { role: "system", content: systemNote }]);
      if (data.error) setError(data.error);
      else setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function approveStage(stage: "evidence" | "assumptions" | "decision") {
    if (!study || loading) return;
    const token = getToken();
    if (!token) {
      setError(ar ? "الرجاء تسجيل الدخول" : "Please sign in");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/approve/${stage}`, {
        method: "POST",
        credentials: "same-origin",
        headers: studyFetchHeaders(token),
        body: JSON.stringify({ approved: true }),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        const message = Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
          : detail || "Failed";
        throw new Error(message);
      }
      applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: ar
            ? `تمت الموافقة على مرحلة ${stage}. الانتقال للمرحلة التالية...`
            : `Approved ${stage} stage. Moving to next phase...`,
        },
      ]);
      if (data.error) setError(data.error);
      else setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function postStudyAction(path: string, body?: Record<string, unknown>) {
    if (!study || loading) return;
    const token = getToken();
    if (!token) {
      setError(ar ? "الرجاء تسجيل الدخول" : "Please sign in");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/${path}`, {
        method: "POST",
        credentials: "same-origin",
        headers: studyFetchHeaders(token),
        body: JSON.stringify(body || {}),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        throw new Error(
          Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
            : detail || "Failed",
        );
      }
      applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function runItemAction(
    target: "claim" | "assumption",
    index: number,
    action: ItemAction,
    currentValue?: string,
  ) {
    if (!study || loading) return;
    const token = getToken();
    if (!token) {
      setError(ar ? "الرجاء تسجيل الدخول" : "Please sign in");
      return;
    }

    let value: string | undefined;
    let note: string | undefined;

    if (action === "edit") {
      const next = window.prompt(
        ar ? "أدخل القيمة الجديدة:" : "Enter the new value:",
        currentValue || "",
      );
      if (next === null) return;
      value = next.trim();
      if (!value) {
        setError(ar ? "القيمة مطلوبة للتعديل" : "Value is required for edit");
        return;
      }
    } else if (action === "request_alternative" || action === "regenerate") {
      const optional = window.prompt(
        ar ? "ملاحظة اختيارية (يمكن تركها فارغة):" : "Optional note (leave blank to skip):",
        "",
      );
      if (optional === null) return;
      note = optional.trim() || undefined;
    }

    setLoading(true);
    setError(null);
    try {
      const body: { target: string; index: number; action: string; value?: string; note?: string } = {
        target,
        index,
        action,
      };
      if (value !== undefined) body.value = value;
      if (note !== undefined) body.note = note;

      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/item-action`, {
        method: "POST",
        credentials: "same-origin",
        headers: studyFetchHeaders(token),
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        const message = Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
          : detail || "Failed";
        throw new Error(message);
      }
      applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
      if (data.error) setError(data.error);
      else setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const phaseLabel = study?.phase ? (PHASE_LABELS[study.phase]?.[locale] ?? study.phase) : "";
  const pendingQuestions = (study?.discovery_questions || []).filter(
    (q) => q.required !== false && !q.answered,
  );
  const showInformationGate =
    study?.phase === "NEEDS_INFORMATION" && pendingQuestions.length === 0;
  const fundingMeta = (study?.workflow_meta?.funding || null) as
    | {
        score_percent?: number;
        blockers?: string[];
        blocker_labels?: Record<string, string>;
        matches?: { name?: string; name_ar?: string; score_percent?: number; reasons?: string[] }[];
        use_of_funds_hints?: string[];
      }
    | null;
  const reportMeta = study?.workflow_meta?.report as Record<string, unknown> | undefined;
  const financialIncomplete = Boolean(
    financial &&
      (financial.status === "MODEL_INCOMPLETE" || financial.reason === "INSUFFICIENT_DATA"),
  );
  const scenarios = (financial?.scenarios || {}) as Record<string, Record<string, unknown>>;

  return (
    <main className="container-page flex min-h-[calc(100vh-4rem)] flex-col py-4" data-testid="v2-study-workspace">
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
            <span
              className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700"
              data-testid="study-phase"
            >
              {phaseLabel}
            </span>
            {study.verdict && (
              <span
                className={`rounded-full px-3 py-1 text-xs font-bold ${VERDICT_COLORS[study.verdict] ?? "bg-slate-100"}`}
                data-testid="study-verdict"
              >
                {study.verdict}
              </span>
            )}
          </div>
        )}
      </header>

      {study && (
        <section
          className="mb-4 grid gap-3 rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-4 md:grid-cols-4"
          data-testid="study-status-strip"
        >
          <div>
            <p className="text-[11px] uppercase tracking-wide text-ink-500">{ar ? "نوع المشروع" : "Project type"}</p>
            <p className="text-sm font-semibold text-ink-900" data-testid="study-archetype">
              {study.profile?.archetype || "—"}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-ink-500">{ar ? "المرحلة الحالية" : "Current phase"}</p>
            <p className="text-sm font-semibold text-ink-900">{phaseLabel || study.phase}</p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-ink-500">{ar ? "الإجراء الحالي" : "Current action"}</p>
            <p className="text-sm font-semibold text-ink-900" data-testid="study-next-action">
              {study.next_action || "—"}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-ink-500">{ar ? "العوائق" : "Blockers"}</p>
            <p className="text-sm font-semibold text-ink-900">
              {study.blocking_reason ||
                (financialIncomplete
                  ? ar
                    ? "نموذج مالي ناقص"
                    : "Incomplete financial model"
                  : pendingQuestions.length
                    ? ar
                      ? `${pendingQuestions.length} أسئلة مطلوبة`
                      : `${pendingQuestions.length} required questions`
                    : "—")}
            </p>
          </div>
        </section>
      )}

      {study?.profile && (
        <div className="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs" data-testid="study-profile-panel">
          <div className="mb-2 flex flex-wrap gap-2">
            <span className="rounded bg-white px-2 py-1 font-medium text-ink-700">{study.profile.archetype}</span>
            <span className="rounded bg-white px-2 py-1 text-ink-600">{study.profile.sector}</span>
            <span className="rounded bg-white px-2 py-1 text-ink-600">{study.profile.stage}</span>
            {study.profile.decision_goal && (
              <span className="rounded bg-white px-2 py-1 text-ink-600">{study.profile.decision_goal}</span>
            )}
            {study.gate_choice && (
              <span className="rounded bg-white px-2 py-1 text-ink-500">
                {ar ? "المسار" : "Path"}: {study.gate_choice}
              </span>
            )}
          </div>
          {missing.length > 0 && (
            <div
              className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900"
              data-testid="missing-information-box"
            >
              <p className="font-semibold">{ar ? "معلومات ناقصة" : "Missing information"}</p>
              <p className="mt-1 text-[11px] text-amber-800">
                {ar
                  ? "المسار المفضّل: إنشاء مسودة دراسة بالذكاء الاصطناعي (بحث عن مصادر). التقدير المؤقت احتياطي؛ الإكمال اليدوي اختياري للبيانات السرية أو غير المتاحة."
                  : "Preferred path: Generate AI Study Draft (research sources). Provisional estimates are a fallback; manual completion is optional for confidential or unavailable data."}
              </p>
            </div>
          )}
        </div>
      )}

      {!!(study?.discovery_questions && study.discovery_questions.length) &&
        (study.phase === "NEEDS_INFORMATION" || study.phase === "UNDERSTANDING") && (
          <DiscoveryQuestionsPanel
            key={`${study.study_id}-${study.discovery_questions.length}-${study.discovery_questions.filter((q) => q.answered).length}`}
            questions={study.discovery_questions}
            ar={ar}
            loading={loading}
            onSubmit={async (answers) => {
              const token = getToken();
              if (!token || !study) return;
              setLoading(true);
              setError(null);
              try {
                const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/answer-questions`, {
                  method: "POST",
                  credentials: "same-origin",
                  headers: studyFetchHeaders(token),
                  body: JSON.stringify({ answers }),
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || "Failed to save answers");
                applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
              } catch (err) {
                setError(err instanceof Error ? err.message : String(err));
              } finally {
                setLoading(false);
              }
            }}
          />
        )}

      {showInformationGate && (
        <div className="mb-3 flex flex-col gap-2" data-testid="information-gate-buttons">
          <button
            type="button"
            onClick={() => void submitInformationGate("research")}
            disabled={loading}
            data-testid="gate-research"
            className="rounded-xl border-2 border-sky-500 bg-sky-600 px-4 py-4 text-left text-base font-bold text-white shadow-sm hover:bg-sky-700 disabled:opacity-50"
          >
            <span className="block">
              {ar ? "إنشاء مسودة دراسة بالذكاء الاصطناعي" : "Generate AI Study Draft"}
            </span>
            <span className="mt-1 block text-xs font-medium text-sky-100">
              {ar
                ? "المفضّل — ابحث عن المعلومات المتاحة من مصادر موثوقة"
                : "Preferred — research available information from trusted sources"}
            </span>
          </button>
          <div className="grid gap-2 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => void submitInformationGate("provisional")}
              disabled={loading}
              data-testid="gate-provisional"
              className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-3 text-left text-sm font-semibold text-emerald-900 shadow-sm hover:bg-emerald-100 disabled:opacity-50"
            >
              <span className="block">
                {ar
                  ? "أنشئ دراسة تقديرية باستخدام تقديرات"
                  : "Create a provisional study using estimates"}
              </span>
              <span className="mt-1 block text-[11px] font-normal text-emerald-800">
                {ar ? "احتياطي عند تعذّر التحقق" : "Fallback when verified data is unavailable"}
              </span>
            </button>
            <button
              type="button"
              onClick={() => void submitInformationGate("manual")}
              disabled={loading}
              data-testid="gate-manual"
              className="rounded-lg border border-slate-200 bg-white px-3 py-3 text-left text-sm font-medium text-ink-700 shadow-sm hover:bg-slate-50 disabled:opacity-50"
            >
              <span className="block">
                {ar ? "أكمل المعلومات الناقصة بنفسي" : "Complete the missing information myself"}
              </span>
              <span className="mt-1 block text-[11px] font-normal text-ink-500">
                {ar ? "اختياري — بيانات سرية أو غير متاحة علناً" : "Optional — confidential or publicly unavailable data"}
              </span>
            </button>
          </div>
        </div>
      )}

      {showFilledPanels && (
        <div
          ref={filledPanelsRef}
          className="mb-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3"
          data-testid="ai-filled-panels"
        >
          <section className="rounded-xl border border-slate-200 bg-white p-3" data-testid="claims-panel">
            <h2 className="text-sm font-semibold text-ink-900">
              {ar ? `الأدلة (${claims.length})` : `Evidence (${claims.length})`}
            </h2>
            <EvidenceStatusBanner
              status={evidenceStatus}
              ar={ar}
              blockingReason={study?.blocking_reason}
            />
            {claims.length === 0 ? (
              <p className="mt-2 text-xs text-ink-500" data-testid="claims-empty-state">
                {ar
                  ? "لا توجد أدلة مدعومة بمصادر بعد. التقديرات الافتراضية لا تُعرض هنا — تظهر تحت الافتراضات فقط."
                  : "No source-backed evidence yet. Provisional estimates are not shown here — they appear under Assumptions only."}
              </p>
            ) : (
              <ul className="mt-2 space-y-2 text-xs text-ink-700">
                {claims.map((claim, idx) => (
                  <li key={`${claim.statement}-${idx}`} className="rounded-lg bg-slate-50 p-2">
                    <p>{claim.statement}</p>
                    <p className="mt-1 text-[11px] text-ink-500">
                      {claim.source_type || "unverified"}
                      {claim.source_title ? ` · ${claim.source_title}` : ""}
                      {typeof claim.confidence === "number"
                        ? ` · ${Math.round(claim.confidence * 100)}%`
                        : ""}
                      {claim.status ? ` · ${claim.status}` : ""}
                    </p>
                    <ItemActionBar
                      ar={ar}
                      loading={loading}
                      showRegenerate={false}
                      onAction={(action) => void runItemAction("claim", idx, action, claim.statement)}
                    />
                  </li>
                ))}
              </ul>
            )}
          </section>

          {(assumptions.length > 0 ||
            study?.phase === "ASSUMPTIONS_REVIEW" ||
            study?.gate_choice === "provisional") && (
            <section
              className="rounded-xl border border-slate-200 bg-white p-3"
              data-testid="assumptions-panel"
            >
              <h2 className="text-sm font-semibold text-ink-900">
                {ar ? `الافتراضات (${assumptions.length})` : `Assumptions (${assumptions.length})`}
              </h2>
              {assumptions.length === 0 ? (
                <p className="mt-2 text-xs text-ink-500">
                  {ar ? "لا توجد افتراضات بعد." : "No assumptions yet."}
                </p>
              ) : (
                <ul className="mt-2 space-y-2 text-xs text-ink-700">
                  {assumptions.map((item, idx) => {
                    const origin = item.origin || "user";
                    const originLabel = ORIGIN_LABELS[origin]?.[locale] ?? origin;
                    const provisional = origin === "provisional_estimate";
                    return (
                      <li key={`${item.key}-${idx}`} className="rounded-lg bg-slate-50 p-2">
                        <div className="mb-1 flex flex-wrap items-center gap-1">
                          <p className="font-medium">{item.key}</p>
                          <span
                            className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                              provisional
                                ? "bg-amber-100 text-amber-900"
                                : "bg-slate-200 text-slate-700"
                            }`}
                            data-testid="assumption-origin-badge"
                            data-origin={origin}
                          >
                            {originLabel}
                          </span>
                          {item.status && (
                            <span className="rounded bg-white px-1.5 py-0.5 text-[10px] text-ink-500">
                              {item.status}
                            </span>
                          )}
                        </div>
                        <p>{item.value}</p>
                        {(item.low || item.base || item.high) && (
                          <p className="mt-1 text-[11px] text-ink-500">
                            L/B/H: {item.low ?? "—"} / {item.base ?? "—"} / {item.high ?? "—"}
                          </p>
                        )}
                        {item.rationale && (
                          <p className="mt-1 text-[11px] text-ink-500">{item.rationale}</p>
                        )}
                        <ItemActionBar
                          ar={ar}
                          loading={loading}
                          showRegenerate
                          onAction={(action) =>
                            void runItemAction("assumption", idx, action, item.value)
                          }
                        />
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          )}

          {(financial || study?.verdict || study?.decision_rationale) && (
            <section className="rounded-xl border border-slate-200 bg-white p-3 md:col-span-2 xl:col-span-3" data-testid="decision-panel">
              <h2 className="text-sm font-semibold text-ink-900">
                {ar ? "التحليل والقرار" : "Analysis & decision"}
              </h2>
              {financialIncomplete && (
                <div
                  className="mt-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-950"
                  data-testid="financial-incomplete"
                >
                  <p className="font-semibold">
                    {String(financial?.status || "MODEL_INCOMPLETE")} — {String(financial?.reason || "INSUFFICIENT_DATA")}
                  </p>
                  <ul className="mt-1 list-disc ps-4">
                    {((financial?.missing_data as string[]) || []).map((m) => (
                      <li key={m}>{m}</li>
                    ))}
                  </ul>
                </div>
              )}
              {financial && !financialIncomplete && (
                <div className="mt-2 grid gap-2 text-xs text-ink-700 sm:grid-cols-4" data-testid="financial-metrics">
                  {"npv" in financial && <p>NPV: {String(financial.npv)}</p>}
                  {"irr" in financial && <p>IRR: {String(financial.irr)}</p>}
                  {"payback_months" in financial && (
                    <p>Payback (months): {String(financial.payback_months)}</p>
                  )}
                  {"capex" in financial && <p>CAPEX: {String(financial.capex)}</p>}
                </div>
              )}
              {Object.keys(scenarios).length > 0 && (
                <div className="mt-3" data-testid="scenarios-panel">
                  <h3 className="text-xs font-semibold text-ink-800">{ar ? "السيناريوهات" : "Scenarios"}</h3>
                  <div className="mt-1 grid gap-2 sm:grid-cols-3">
                    {["BASE", "UPSIDE", "DOWNSIDE", "base", "optimistic", "conservative"]
                      .filter((k, i, arr) => scenarios[k] && arr.indexOf(k) === i)
                      .filter((k) => {
                        // Prefer BASE/UPSIDE/DOWNSIDE when present
                        if (scenarios.BASE && ["base", "optimistic", "conservative"].includes(k)) return false;
                        return true;
                      })
                      .map((key) => (
                        <div key={key} className="rounded-lg bg-slate-50 p-2 text-xs">
                          <p className="font-semibold">{key}</p>
                          <p>NPV: {String(scenarios[key]?.npv ?? "—")}</p>
                          <p>IRR: {String(scenarios[key]?.irr ?? "—")}</p>
                        </div>
                      ))}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <button
                      type="button"
                      data-testid="scenario-challenge-customers"
                      disabled={loading}
                      onClick={() =>
                        void postStudyAction("scenario-challenge", {
                          revenue_multiplier: 0.7,
                          note: ar ? "خفض عدد العملاء 30%" : "Cut customers 30%",
                        })
                      }
                      className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
                    >
                      {ar ? "خفض العملاء 30%" : "Customers −30%"}
                    </button>
                    <button
                      type="button"
                      data-testid="scenario-challenge-cost"
                      disabled={loading}
                      onClick={() =>
                        void postStudyAction("scenario-challenge", {
                          cost_multiplier: 1.15,
                          note: ar ? "تكلفة البناء ارتفعت 15%" : "Construction cost +15%",
                        })
                      }
                      className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium hover:bg-slate-50 disabled:opacity-50"
                    >
                      {ar ? "تكلفة +15%" : "Cost +15%"}
                    </button>
                  </div>
                </div>
              )}
              {(study?.decision_risks || []).length > 0 && (
                <div className="mt-3" data-testid="risks-panel">
                  <h3 className="text-xs font-semibold text-ink-800">{ar ? "المخاطر" : "Risks"}</h3>
                  <ul className="mt-1 list-disc ps-4 text-xs text-ink-700">
                    {study!.decision_risks!.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                </div>
              )}
              {study?.decision_rationale && (
                <p className="mt-2 whitespace-pre-wrap text-xs text-ink-700">{study.decision_rationale}</p>
              )}
              {(study?.decision_conditions || []).length > 0 && (
                <ul className="mt-2 list-disc ps-4 text-xs text-ink-600">
                  {study!.decision_conditions!.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              )}
              {study?.phase === "DECISION_READY" && study.verdict && (
                <button
                  type="button"
                  data-testid="approve-decision"
                  disabled={loading || ["INSUFFICIENT_EVIDENCE", "NEED_MORE_VALIDATION"].includes(study.verdict)}
                  onClick={() => void approveStage("decision")}
                  className="mt-3 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                >
                  {ar ? "الموافقة على القرار والمتابعة للتمويل" : "Approve decision & continue to funding"}
                </button>
              )}
            </section>
          )}

          {(fundingMeta || study?.phase === "FUNDING_READY") && (
            <section className="rounded-xl border border-slate-200 bg-white p-3 md:col-span-2" data-testid="funding-panel">
              <h2 className="text-sm font-semibold text-ink-900">
                {ar ? "التمويل الذكي" : "Intelligent Funding"}
              </h2>
              {fundingMeta ? (
                <div className="mt-2 space-y-2 text-xs text-ink-700">
                  <p data-testid="funding-score">
                    {ar ? "جاهزية مفسَّرة" : "Explained readiness"}: {fundingMeta.score_percent ?? 0}%
                  </p>
                  {(fundingMeta.blockers || []).length > 0 && (
                    <ul className="list-disc ps-4 text-amber-800">
                      {(fundingMeta.blockers || []).map((b) => (
                        <li key={b}>{fundingMeta.blocker_labels?.[b] || b}</li>
                      ))}
                    </ul>
                  )}
                  {(fundingMeta.use_of_funds_hints || []).length > 0 && (
                    <p>
                      {ar ? "استخدام التمويل" : "Use of funds"}:{" "}
                      {(fundingMeta.use_of_funds_hints || []).join(" · ")}
                    </p>
                  )}
                  <ul className="space-y-1">
                    {(fundingMeta.matches || []).slice(0, 4).map((m) => (
                      <li key={`${m.name}-${m.score_percent}`} className="rounded bg-slate-50 p-2">
                        <p className="font-medium">{ar ? m.name_ar || m.name : m.name}</p>
                        <p className="text-[11px] text-ink-500">{m.score_percent}% — {(m.reasons || [])[0]}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="mt-2 text-xs text-ink-500">{ar ? "جارٍ تجهيز التمويل..." : "Preparing funding..."}</p>
              )}
              <button
                type="button"
                data-testid="generate-report"
                disabled={loading}
                onClick={() => void postStudyAction("generate-report")}
                className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                {ar ? "إنشاء التقرير النهائي" : "Generate final report"}
              </button>
              {reportMeta && (
                <p className="mt-2 text-xs text-emerald-700" data-testid="report-ready">
                  {ar ? "ملخص التقرير جاهز من حالة الدراسة المحفوظة." : "Report summary ready from persisted study state."}
                </p>
              )}
            </section>
          )}
        </div>
      )}

      {(study?.phase === "EVIDENCE_REVIEW" || study?.phase === "ASSUMPTIONS_REVIEW") && (
        <div className="mb-3 flex gap-2">
          {study.phase === "EVIDENCE_REVIEW" && (
            <button
              type="button"
              onClick={() => void approveStage("evidence")}
              disabled={loading || claims.length === 0}
              data-testid="approve-evidence"
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {ar ? "الموافقة على الأدلة" : "Approve Evidence"}
            </button>
          )}
          {study.phase === "ASSUMPTIONS_REVIEW" && (
            <button
              type="button"
              onClick={() => void approveStage("assumptions")}
              disabled={loading || assumptions.length === 0}
              data-testid="approve-assumptions"
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {ar ? "الموافقة على الافتراضات" : "Approve Assumptions"}
            </button>
          )}
        </div>
      )}

      <div className="flex-1 overflow-y-auto rounded-xl border border-slate-200 bg-white p-4">
        {hydrating && (
          <div className="flex h-full items-center justify-center text-sm text-ink-500">
            {ar ? "جارٍ تحميل الدراسة..." : "Loading study..."}
          </div>
        )}
        {!hydrating && messages.length === 0 && (
          <div className="flex h-full items-center justify-center text-center text-ink-400">
            <div>
              <p className="text-lg font-medium">
                {ar ? "ابدأ بوصف مشروعك" : "Start by describing your project"}
              </p>
              <p className="mt-2 text-sm">
                {ar
                  ? "اكتب وصفاً لمشروعك وسيقوم المحرك الذكي بتحليله وإرشادك خطوة بخطوة."
                  : "Write a description of your project and the AI engine will analyze it and guide you step by step."}
              </p>
            </div>
          </div>
        )}
        {!hydrating &&
          messages.map((msg, i) => (
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
        <p role="alert" className="mt-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void sendMessage();
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
