"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";
import { getToken, API_BASE } from "@/lib/api";
import { ArchetypeClassificationPanel } from "@/components/study/ArchetypeClassificationPanel";
import { DiscoveryQuestionsPanel } from "@/components/study/DiscoveryQuestionsPanel";
import { AssumptionReviewPanel } from "@/components/study/AssumptionReviewPanel";
import { KnowledgePanel } from "@/components/study/KnowledgePanel";
import { StudyJourneyNav, StudyLateStagePanels } from "@/components/study/StudyJourneyPanels";
import { archetypeLabel } from "@/lib/archetypeLabels";

type Message = {
  role: "user" | "assistant" | "system";
  content: string;
};

type Claim = {
  statement: string;
  source_type?: string;
  confidence?: number;
  source_url?: string | null;
};

type Assumption = {
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

type DiscoveryQuestion = {
  id: string;
  prompt?: string;
  question?: string;
  explanation?: string;
  description?: string;
  category?: string;
  answer_type?: string;
  question_type?: string;
  options?: string[];
  required?: boolean;
  allow_ai_estimate?: boolean;
  unit?: string | null;
  field_key?: string | null;
  answer?: string | string[] | number | boolean | null;
  answered?: boolean;
  ai_estimated?: boolean;
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
    archetype_confirmed?: boolean;
  } | null;
  claims?: Claim[];
  assumptions?: Assumption[];
  claims_count?: number;
  assumptions_count?: number;
  discovery_questions?: DiscoveryQuestion[];
  structured_answers?: Record<string, unknown>;
  assumptions_version?: number;
  archetype_options?: { id: string; label: string; label_en?: string }[];
  financial_results?: Record<string, unknown> | null;
  verdict: string | null;
  decision_rationale: string | null;
  decision_conditions?: string[];
  decision_risks?: string[];
  messages?: Message[];
  next_action: string | null;
  error: string | null;
};

const PHASE_LABELS: Record<string, { ar: string; en: string }> = {
  DRAFT: { ar: "مسودة", en: "Draft" },
  ARCHETYPE_CLASSIFICATION: { ar: "تصنيف المشروع", en: "Archetype Classification" },
  UNDERSTANDING: { ar: "فهم المشروع", en: "Understanding" },
  NEEDS_INFORMATION: { ar: "جمع المعلومات", en: "Gathering Info" },
  EVIDENCE_REVIEW: { ar: "مراجعة الأدلة", en: "Evidence Review" },
  ASSUMPTIONS_REVIEW: { ar: "مراجعة الافتراضات", en: "Assumptions Review" },
  READY_FOR_ANALYSIS: { ar: "جاهز للتحليل", en: "Ready for Analysis" },
  ANALYZED: { ar: "تم التحليل", en: "Analyzed" },
  DECISION_READY: { ar: "القرار جاهز", en: "Decision Ready" },
  FUNDING_READY: { ar: "جاهز للتمويل", en: "Funding Ready" },
  REPORT_READY: { ar: "التقرير جاهز", en: "Report Ready" },
};

const VERDICT_COLORS: Record<string, string> = {
  GO: "bg-emerald-100 text-emerald-800",
  GO_WITH_CONDITIONS: "bg-amber-100 text-amber-800",
  DEFER: "bg-blue-100 text-blue-800",
  NO_GO: "bg-red-100 text-red-800",
  INSUFFICIENT_EVIDENCE: "bg-slate-100 text-slate-800",
};

function sanitizeChatContent(text: string): string {
  if (!text) return "";
  let cleaned = text.replace(/```(?:json|javascript|js|tool|xml)?[\s\S]*?```/gi, "");
  cleaned = cleaned.replace(
    /\b(req_[a-zA-Z0-9]+|chatcmpl-[a-zA-Z0-9]+|call_[a-zA-Z0-9]+|org_[a-zA-Z0-9]+|proj_[a-zA-Z0-9]+)\b/gi,
    "[redacted]",
  );
  cleaned = cleaned.replace(
    /\b(llama-[\w.\-]+|gpt-oss-[\w.\-]+|gpt-4[\w.\-]*|mixtral-[\w.\-]+|gemma-[\w.\-]+|groq\/[^\s,;]+)\b/gi,
    "[model]",
  );
  cleaned = cleaned.replace(
    /https?:\/\/[^\s]*(?:console\.groq\.com|platform\.openai\.com|billing|usage|rate-limits)[^\s]*/gi,
    "[link]",
  );
  cleaned = cleaned.replace(/\b\d+\s*[KkMm]?\s*(?:TPM|TPD|tokens?\s*per\s*day)\b/gi, "[limit]");
  cleaned = cleaned.replace(/<tool_call>[\s\S]*?<\/tool_call>/gi, "");
  // Drop bare JSON blobs and obvious stack / HTTP dumps.
  const lines = cleaned.split("\n").filter((line) => {
    if (/Traceback \(most recent call last\)|File "[^"]+", line \d+/i.test(line)) return false;
    if (/Error code:\s*\d+|rate[_ ]?limit|\b(429|503|401|403)\b/i.test(line)) return false;
    if (/(Exception|Error):\s*.{0,40}(groq|openai|httpx|api\.)/i.test(line)) return false;
    return true;
  });
  cleaned = lines.join("\n").trim();
  if (/^\s*[\{\[][\s\S]*[\}\]]\s*$/.test(cleaned)) return "";
  if (/fill evidence now|output json inside|strict rules:/i.test(cleaned)) return "";
  return cleaned.replace(/\n{3,}/g, "\n\n").trim();
}

/** Session auth uses an HTTP-only cookie; never send Authorization: Bearer session. */
function studyFetchHeaders(token: string): HeadersInit {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token && token !== "session") {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

function applyStudyPayload(
  data: StudyInfo,
  setStudy: (s: StudyInfo) => void,
  setMessages: (msgs: Message[] | ((prev: Message[]) => Message[])) => void,
  opts?: { mergeAssistantStub?: string; replaceMessages?: boolean },
) {
  setStudy(data);
  const hydrated = (data.messages || [])
    .map((m) => ({
      role: m.role,
      content: m.role === "assistant" ? sanitizeChatContent(m.content) : m.content,
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
  const [selectedArchetype, setSelectedArchetype] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const filledPanelsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if ((study?.claims_count || 0) > 0 || (study?.assumptions_count || 0) > 0) {
      filledPanelsRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, study?.claims_count, study?.assumptions_count]);

  useEffect(() => {
    // Owner reopen path: `/studies/new` must not orphan an existing V2 study.
    if (studyId !== "new") return;
    const token = getToken();
    if (!token || !projectId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v2/studies`, {
          credentials: "same-origin",
          headers: studyFetchHeaders(token),
        });
        if (!res.ok) return;
        const data = (await res.json()) as { studies?: Array<{ study_id: string; project_id?: string | null }> };
        const existing = (data.studies || []).find((s) => String(s.project_id ?? "") === String(projectId));
        if (!cancelled && existing?.study_id) {
          router.replace(`/projects/${projectId}/studies/${existing.study_id}/workspace`);
        }
      } catch {
        /* keep "new" create path if list fails */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [studyId, projectId, router]);

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
        mergeAssistantStub: ar ? "تم إنشاء الدراسة. جارٍ تحليل مشروعك..." : "Study created. Analyzing your project...",
      });

      // If API returned assistant text but messages were empty, append response.
      if (data.response) {
        const cleaned = sanitizeChatContent(data.response);
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
            }
          : data,
      );

      if (data.messages?.length) {
        applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
      } else if (data.response) {
        const cleaned = sanitizeChatContent(data.response);
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


  async function confirmArchetype() {
    if (!study || loading) return;
    const token = getToken();
    if (!token) {
      setError(ar ? "الرجاء تسجيل الدخول" : "Please sign in");
      return;
    }
    const archetype = selectedArchetype || study.profile?.archetype;
    if (!archetype || archetype === "unknown") {
      setError(ar ? "اختر نوع المشروع أولاً" : "Select a project archetype first");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/archetype`, {
        method: "POST",
        credentials: "same-origin",
        headers: studyFetchHeaders(token),
        body: JSON.stringify({ archetype, approved: true }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to confirm archetype");
      applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function submitStructuredAnswers(payload: {
    answers: { id: string; value: unknown }[];
    aiEstimates: string[];
  }) {
    if (!study || loading) return;
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const answers: Record<string, unknown> = {};
      for (const a of payload.answers) answers[a.id] = a.value;
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/structured-answers`, {
        method: "POST",
        credentials: "same-origin",
        headers: studyFetchHeaders(token),
        body: JSON.stringify({
          answers,
          ai_estimates: payload.aiEstimates || [],
          mark_answered: true,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to submit answers");
      applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function regenerateAssumptions() {
    if (!study || loading) return;
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/assumptions/regenerate`, {
        method: "POST",
        credentials: "same-origin",
        headers: studyFetchHeaders(token),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to regenerate");
      applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function editAssumption(key: string, value: string) {
    if (!study || loading) return;
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/assumptions/edit`, {
        method: "POST",
        credentials: "same-origin",
        headers: studyFetchHeaders(token),
        body: JSON.stringify({ key, value }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to edit assumption");
      applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
      if (data.error) setError(data.error);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function assumptionCardAction(key: string, action: "approve" | "reject" | "regenerate") {
    if (!study || loading) return;
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/assumptions/action`, {
        method: "POST",
        credentials: "same-origin",
        headers: studyFetchHeaders(token),
        body: JSON.stringify({ key, action }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Failed to ${action} assumption`);
      applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
      if (data.error) setError(data.error);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function approveStage(stage: string) {
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
      if (stage === "profile" && data.phase === "NEEDS_INFORMATION") {
        throw new Error(
          ar
            ? "تعذر متابعة التأكيد. حدّث الصفحة وحاول مرة أخرى."
            : "Confirm did not advance. Refresh the page and try again.",
        );
      }
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content:
            stage === "profile"
              ? ar
                ? "تم التأكيد. جارٍ تعبئة الأدلة والافتراضات بالتقديرات..."
                : "Confirmed. Filling evidence and assumptions with estimates..."
              : ar
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


  async function continueStudy() {
    if (!study || loading) return;
    const token = getToken();
    if (!token) {
      setError(ar ? "الرجاء تسجيل الدخول" : "Please sign in");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/v2/studies/${study.study_id}/continue`, {
        method: "POST",
        credentials: "same-origin",
        headers: studyFetchHeaders(token),
      });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        const message = Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
          : detail || "Failed to continue";
        throw new Error(message);
      }
      applyStudyPayload(data, setStudy, setMessages, { replaceMessages: true });
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: ar ? "تم الانتقال إلى المرحلة التالية." : "Advanced to the next study stage.",
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

  const phaseLabel = study?.phase ? (PHASE_LABELS[study.phase]?.[locale] ?? study.phase) : "";
  const claims = study?.claims || [];
  const assumptions = study?.assumptions || [];
  const financial = study?.financial_results || null;
  const missing = study?.profile?.missing_information || [];

  return (
    <main className="container-page flex h-[calc(100vh-4rem)] flex-col py-4" data-testid="v2-study-workspace">
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
            <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700" data-testid="study-phase">
              {phaseLabel}
            </span>
            {study.verdict && (
              <span className={`rounded-full px-3 py-1 text-xs font-bold ${VERDICT_COLORS[study.verdict] ?? "bg-slate-100"}`} data-testid="study-verdict">
                {study.verdict}
              </span>
            )}
          </div>
        )}
      </header>

      {study?.phase ? <StudyJourneyNav ar={ar} phase={study.phase} /> : null}

      {study?.profile && (
        <div className="mb-3 rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs" data-testid="study-profile-panel">
          <div className="mb-2 flex flex-wrap gap-2">
            <span className="rounded bg-white px-2 py-1 font-medium text-ink-700">
              {archetypeLabel(study.profile.archetype, ar ? "ar" : "en")}
            </span>
            <span className="rounded bg-white px-2 py-1 text-ink-600">{study.profile.sector}</span>
            <span className="rounded bg-white px-2 py-1 text-ink-600">{study.profile.stage}</span>
            {study.profile.decision_goal && (
              <span className="rounded bg-white px-2 py-1 text-ink-600">{study.profile.decision_goal}</span>
            )}
          </div>
          {study.phase === "NEEDS_INFORMATION" && (study.discovery_questions?.length || 0) > 0 ? (
            <div
              className="rounded-lg border border-sky-200 bg-sky-50 p-3 text-sky-950"
              data-testid="discovery-advisor-hint"
            >
              <p className="font-semibold">
                {ar ? "مقابلة اكتشاف مع مستشار الذكاء الاصطناعي" : "AI consultant discovery interview"}
              </p>
              <p className="mt-1 text-[11px] text-sky-900">
                {ar
                  ? "بدلاً من قائمة معلومات ناقصة ثابتة، أجب على أسئلة المستشار أو اختر «دع الذكاء الاصطناعي يقدّر»."
                  : "Instead of a static missing-information list, answer the advisor’s questions or choose “Let AI estimate”."}
              </p>
            </div>
          ) : null}
          {/* Legacy static missing list removed from primary UX; keep test id absent during interview. */}
          {missing.length > 0 &&
            study.phase !== "NEEDS_INFORMATION" &&
            !(study.discovery_questions?.length) && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900" data-testid="missing-information-box">
              <p className="font-semibold">{ar ? "معلومات ناقصة" : "Missing information"}</p>
              <ul className="mt-1 list-disc ps-4">
                {missing.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}


      <KnowledgePanel ar={ar} apiBase={API_BASE} getToken={getToken} />

      {study?.phase === "ARCHETYPE_CLASSIFICATION" && (
        <ArchetypeClassificationPanel
          ar={ar}
          loading={loading}
          suggested={study.profile?.archetype}
          selected={selectedArchetype}
          onSelect={setSelectedArchetype}
          onConfirm={() => void confirmArchetype()}
        />
      )}

      {(study?.phase === "NEEDS_INFORMATION" || study?.phase === "ARCHETYPE_CLASSIFICATION") &&
        (study?.discovery_questions?.length || 0) > 0 &&
        study.profile?.archetype_confirmed && (
          <DiscoveryQuestionsPanel
            questions={study.discovery_questions || []}
            ar={ar}
            loading={loading}
            onSubmit={submitStructuredAnswers}
          />
        )}

      {study?.phase === "ASSUMPTIONS_REVIEW" && (
        <AssumptionReviewPanel
          assumptions={study.assumptions || []}
          ar={ar}
          loading={loading}
          error={error || study.error}
          onApproveAll={() => approveStage("assumptions")}
          onRegenerateAll={regenerateAssumptions}
          onEdit={editAssumption}
          onCardAction={assumptionCardAction}
        />
      )}

      {study?.phase ? (
        <StudyLateStagePanels
          ar={ar}
          phase={study.phase}
          loading={loading}
          financial={study.financial_results}
          risks={study.decision_risks || []}
          verdict={study.verdict}
          rationale={study.decision_rationale}
          conditions={study.decision_conditions || []}
          onContinue={() => void continueStudy()}
        />
      ) : null}

      {(claims.length > 0 || assumptions.length > 0 || financial || study?.verdict) && (
        <div
          ref={filledPanelsRef}
          className="mb-3 grid max-h-56 gap-3 overflow-y-auto md:grid-cols-2 xl:grid-cols-3"
          data-testid="ai-filled-panels"
        >
          {claims.length > 0 && (
            <section className="rounded-xl border border-slate-200 bg-white p-3" data-testid="claims-panel">
              <h2 className="text-sm font-semibold text-ink-900">
                {ar ? `الأدلة (${claims.length})` : `Evidence (${claims.length})`}
              </h2>
              <ul className="mt-2 space-y-2 text-xs text-ink-700">
                {claims.map((claim, idx) => (
                  <li key={`${claim.statement}-${idx}`} className="rounded-lg bg-slate-50 p-2">
                    <p>{claim.statement}</p>
                    <p className="mt-1 text-[11px] text-ink-500">
                      {claim.source_type || "unverified"}
                      {typeof claim.confidence === "number" ? ` · ${Math.round(claim.confidence * 100)}%` : ""}
                    </p>
                  </li>
                ))}
              </ul>
            </section>
          )}
          {assumptions.length > 0 && (
            <section className="rounded-xl border border-slate-200 bg-white p-3" data-testid="assumptions-panel">
              <h2 className="text-sm font-semibold text-ink-900">
                {ar ? `الافتراضات (${assumptions.length})` : `Assumptions (${assumptions.length})`}
              </h2>
              <ul className="mt-2 space-y-2 text-xs text-ink-700">
                {assumptions.map((item) => (
                  <li key={item.key} className="rounded-lg bg-slate-50 p-2" data-ai-estimated={item.ai_estimated ? "true" : "false"}>
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium">{item.label_en || item.label_ar || item.key}</p>
                      {(item.ai_estimated || (item.source || "").toLowerCase().includes("ai estimated")) && (
                        <span className="rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-bold text-violet-800">
                          {ar ? "مقدّر بالذكاء الاصطناعي" : "AI Estimated"}
                        </span>
                      )}
                    </div>
                    <p>{item.value}</p>
                    {(item.low || item.base || item.high) && (
                      <p className="mt-1 text-[11px] text-ink-500">
                        L/B/H: {item.low ?? "—"} / {item.base ?? "—"} / {item.high ?? "—"}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
          {(financial || study?.verdict || study?.decision_rationale) && (
            <section className="rounded-xl border border-slate-200 bg-white p-3" data-testid="decision-panel">
              <h2 className="text-sm font-semibold text-ink-900">
                {ar ? "التحليل والقرار" : "Analysis & decision"}
              </h2>
              {financial && (
                <div className="mt-2 space-y-1 text-xs text-ink-700">
                  {"npv" in financial && <p>NPV: {String(financial.npv)}</p>}
                  {"irr" in financial && (
                    <p data-testid="workspace-irr">
                      IRR:{" "}
                      {String(
                        (financial as { irr_display?: string }).irr_display ||
                          (financial.irr == null
                            ? ar
                              ? "لا يمكن حساب معدل العائد الداخلي لهذه التدفقات النقدية."
                              : "IRR cannot be calculated for these cash flows."
                            : financial.irr),
                      )}
                    </p>
                  )}
                  {"payback_months" in financial && <p>Payback (months): {String(financial.payback_months)}</p>}
                  {"capex" in financial && <p>CAPEX: {String(financial.capex)}</p>}
                  {Array.isArray((financial as { warnings?: string[] }).warnings) &&
                    ((financial as { warnings?: string[] }).warnings || []).length > 0 && (
                      <ul data-testid="workspace-financial-warnings" className="mt-2 space-y-1 text-amber-800">
                        {((financial as { warnings?: string[] }).warnings || []).map((w) => (
                          <li key={w}>⚠ {w}</li>
                        ))}
                      </ul>
                    )}
                </div>
              )}
              {study?.decision_rationale && (
                <p className="mt-2 text-xs text-ink-700 whitespace-pre-wrap">{study.decision_rationale}</p>
              )}
              {(study?.decision_conditions || []).length > 0 && (
                <ul className="mt-2 list-disc ps-4 text-xs text-ink-600">
                  {study!.decision_conditions!.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>
      )}

      {study?.phase === "EVIDENCE_REVIEW" && (
        <div className="mb-3 flex gap-2">
          <button
            type="button"
            onClick={() => approveStage("evidence")}
            disabled={loading || claims.length === 0}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {ar ? "الموافقة على الأدلة" : "Approve Evidence"}
          </button>
        </div>
      )}

      {/* Legacy confirm shortcut: only when no Discovery Interview questions are present */}
      {study?.phase === "NEEDS_INFORMATION" &&
        missing.length === 0 &&
        !(study.discovery_questions?.length) && (
        <div className="mb-3 flex gap-2">
          <button
            type="button"
            onClick={() => approveStage("profile")}
            disabled={loading}
            data-testid="confirm-profile-btn"
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            {loading
              ? ar
                ? "جارٍ المتابعة..."
                : "Continuing..."
              : ar
                ? "تأكيد الملف الشخصي والمتابعة"
                : "Confirm Profile & continue"}
          </button>
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
              <p className="text-lg font-medium">{ar ? "ابدأ بوصف مشروعك" : "Start by describing your project"}</p>
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
        <p role="alert" className="mt-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>
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
