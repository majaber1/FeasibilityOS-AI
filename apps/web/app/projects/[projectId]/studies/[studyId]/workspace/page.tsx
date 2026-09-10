"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";
import { getToken, API_BASE } from "@/lib/api";

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
};

type ReportSection = {
  title?: string;
  summary?: string;
  items?: unknown[];
  metrics?: Record<string, unknown>;
  verdict?: string | null;
  rationale?: string | null;
  conditions?: string[];
  decision_version?: number;
};

type FeasibilityReport = {
  title?: string;
  generated_at?: string;
  verdict?: string | null;
  section_order?: string[];
  sections?: Record<string, ReportSection>;
  evidence_confidence_mean?: number | null;
  evidence_confidence_threshold?: number;
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
  } | null;
  claims?: Claim[];
  assumptions?: Assumption[];
  claims_count?: number;
  assumptions_count?: number;
  financial_results?: Record<string, unknown> | null;
  assumptions_version?: number;
  assumptions_history?: Array<Record<string, unknown>>;
  report?: FeasibilityReport | null;
  report_outline?: Record<string, unknown> | null;
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

  useEffect(() => {
    if ((study?.claims_count || 0) > 0 || (study?.assumptions_count || 0) > 0) {
      filledPanelsRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, study?.claims_count, study?.assumptions_count]);

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

  const phaseLabel = study?.phase ? (PHASE_LABELS[study.phase]?.[locale] ?? study.phase) : "";
  const claims = study?.claims || [];
  const assumptions = study?.assumptions || [];
  const financial = study?.financial_results || null;
  const report =
    study?.report ||
    ((financial && typeof financial === "object" && "report" in financial
      ? (financial.report as FeasibilityReport)
      : null) ??
      null);
  const reportSections = report?.sections || null;
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

      {!getToken() && (
        <div
          className="mb-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
          data-testid="workspace-auth-required"
        >
          {ar
            ? "يلزم تسجيل الدخول لفتح مساحة عمل الدراسة مباشرة. "
            : "Sign in is required to open this study workspace URL directly. "}
          <Link href="/login" className="font-semibold underline">
            {ar ? "تسجيل الدخول" : "Sign in"}
          </Link>
        </div>
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
          </div>
          {missing.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-amber-900" data-testid="missing-information-box">
              <p className="font-semibold">{ar ? "معلومات ناقصة" : "Missing information"}</p>
              <p className="mt-1 text-[11px] text-amber-800">
                {ar
                  ? "لا يلزم تعبئة كل عنصر يدوياً. اضغط الزر الأخضر فيستخدم الذكاء الاصطناعي تقديرات واضحة ويكمل الدراسة."
                  : "You do not need to answer every item. Press the green button and AI will fill explicit estimates, then continue the study."}
              </p>
              <ul className="mt-1 list-disc ps-4">
                {missing.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              {study.phase === "NEEDS_INFORMATION" && (
                <button
                  type="button"
                  onClick={() => approveStage("profile")}
                  disabled={loading}
                  data-testid="confirm-profile-btn"
                  className="mt-3 w-full rounded-lg bg-emerald-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50"
                >
                  {loading
                    ? ar
                      ? "جارٍ تعبئة التقديرات..."
                      : "Filling estimates..."
                    : ar
                      ? "تأكيد ومتابعة — الذكاء الاصطناعي سيقدّر الباقي الآن"
                      : "Confirm & continue — AI will estimate the rest now"}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {reportSections && (
        <div
          className="mb-3 max-h-72 overflow-y-auto rounded-xl border border-slate-200 bg-white p-3"
          data-testid="feasibility-report-panel"
        >
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-ink-900">
              {report?.title || (ar ? "تقرير الجدوى" : "Feasibility Report")}
            </h2>
            {report?.verdict && (
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${VERDICT_COLORS[report.verdict] ?? "bg-slate-100"}`}
                data-testid="report-verdict"
              >
                {report.verdict}
              </span>
            )}
          </div>
          {typeof report?.evidence_confidence_mean === "number" && (
            <p className="mb-2 text-[11px] text-ink-500" data-testid="report-evidence-confidence">
              Evidence confidence mean: {report.evidence_confidence_mean.toFixed(2)}
              {typeof report.evidence_confidence_threshold === "number"
                ? ` (threshold ${report.evidence_confidence_threshold.toFixed(2)})`
                : ""}
            </p>
          )}
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3" data-testid="report-sections">
            {(report?.section_order || Object.keys(reportSections)).map((key) => {
              const section = reportSections[key];
              if (!section) return null;
              return (
                <section
                  key={key}
                  className="rounded-lg bg-slate-50 p-2 text-xs text-ink-700"
                  data-testid={`report-section-${key}`}
                >
                  <h3 className="font-semibold text-ink-900">{section.title || key}</h3>
                  {section.summary && <p className="mt-1 text-[11px] text-ink-500">{section.summary}</p>}
                  {section.verdict && (
                    <p className="mt-1 font-medium" data-testid="report-decision-verdict">
                      Verdict: {section.verdict}
                    </p>
                  )}
                  {section.rationale && (
                    <p className="mt-1 whitespace-pre-wrap text-[11px]">{section.rationale}</p>
                  )}
                  {section.metrics && (
                    <ul className="mt-1 space-y-0.5 text-[11px]">
                      {Object.entries(section.metrics)
                        .filter(([, v]) => v != null && typeof v !== "object")
                        .slice(0, 6)
                        .map(([k, v]) => (
                          <li key={k}>
                            {k}: {String(v)}
                          </li>
                        ))}
                    </ul>
                  )}
                  {Array.isArray(section.items) && section.items.length > 0 && (
                    <ul className="mt-1 max-h-28 list-disc space-y-1 overflow-y-auto ps-4 text-[11px]">
                      {section.items.slice(0, 8).map((item, idx) => (
                        <li key={idx}>
                          {typeof item === "string"
                            ? item
                            : typeof item === "object" && item !== null
                              ? "statement" in item
                                ? String((item as Claim).statement)
                                : "key" in item
                                  ? `${(item as Assumption).key}: ${(item as Assumption).value}`
                                  : JSON.stringify(item).slice(0, 120)
                              : String(item)}
                        </li>
                      ))}
                    </ul>
                  )}
                  {(section.conditions || []).length > 0 && (
                    <ul className="mt-1 list-disc ps-4 text-[11px] text-ink-600">
                      {section.conditions!.map((c) => (
                        <li key={c}>{c}</li>
                      ))}
                    </ul>
                  )}
                </section>
              );
            })}
          </div>
        </div>
      )}

      {(() => {
        const history = study?.assumptions_history || [];
        const changeRaw =
          financial && typeof financial === "object" ? financial.financial_change : null;
        const change =
          changeRaw && typeof changeRaw === "object"
            ? (changeRaw as Record<string, unknown>)
            : null;
        if (history.length === 0 && !change) return null;
        return (
          <div
            className="mb-3 rounded-xl border border-slate-200 bg-white p-3 text-xs"
            data-testid="assumption-history-panel"
          >
            <h2 className="text-sm font-semibold text-ink-900">
              {ar ? "تفسير تغيّر NPV وإصدارات الافتراضات" : "NPV change & assumption versions"}
            </h2>
            <p className="mt-1 text-[11px] text-ink-500" data-testid="assumptions-version-label">
              {ar ? "إصدار الافتراضات الحالي:" : "Current assumptions version:"}{" "}
              {study?.assumptions_version ?? 0}
            </p>
            {change && (
              <div className="mt-2 rounded-lg bg-slate-50 p-2" data-testid="npv-change-explanation">
                <p className="font-medium text-ink-800">
                  NPV: {String(change.previous_npv ?? "—")}
                  {" → "}
                  {String(
                    (financial as Record<string, unknown>).npv ?? change.npv ?? "—",
                  )}
                  {change.npv_delta != null ? ` (Δ ${String(change.npv_delta)})` : ""}
                </p>
                <p className="mt-1 whitespace-pre-wrap text-[11px] text-ink-600">
                  {String(change.explanation || "")}
                </p>
              </div>
            )}
            <ul className="mt-2 max-h-40 space-y-2 overflow-y-auto" data-testid="assumption-history-list">
              {[...history].reverse().map((entry, idx) => (
                <li key={idx} className="rounded-lg bg-slate-50 p-2">
                  <p className="font-medium">
                    v{String(entry.version ?? "?")}
                    {entry.kind ? ` · ${String(entry.kind)}` : ""}
                    {entry.npv_at_version != null ? ` · NPV ${String(entry.npv_at_version)}` : ""}
                  </p>
                  {Array.isArray(entry.changed_keys) && entry.changed_keys.length > 0 && (
                    <p className="text-[11px] text-ink-500">
                      Changed: {(entry.changed_keys as unknown[]).map(String).join(", ")}
                    </p>
                  )}
                  {entry.note ? (
                    <p className="mt-1 whitespace-pre-wrap text-[11px] text-ink-600">
                      {String(entry.note)}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        );
      })()}

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
                  <li key={item.key} className="rounded-lg bg-slate-50 p-2">
                    <p className="font-medium">{item.key}</p>
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
                  {"irr" in financial && <p>IRR: {String(financial.irr)}</p>}
                  {"payback_months" in financial && <p>Payback (months): {String(financial.payback_months)}</p>}
                  {"capex" in financial && <p>CAPEX: {String(financial.capex)}</p>}
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

      {(study?.phase === "EVIDENCE_REVIEW" || study?.phase === "ASSUMPTIONS_REVIEW") && (
        <div className="mb-3 flex gap-2">
          {study.phase === "EVIDENCE_REVIEW" && (
            <button
              type="button"
              onClick={() => approveStage("evidence")}
              disabled={loading || claims.length === 0}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {ar ? "الموافقة على الأدلة" : "Approve Evidence"}
            </button>
          )}
          {study.phase === "ASSUMPTIONS_REVIEW" && (
            <button
              type="button"
              onClick={() => approveStage("assumptions")}
              disabled={loading || assumptions.length === 0}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
            >
              {ar ? "الموافقة على الافتراضات" : "Approve Assumptions"}
            </button>
          )}
        </div>
      )}

      {/* Keep Confirm available even when missing list is empty but phase is still gated */}
      {study?.phase === "NEEDS_INFORMATION" && missing.length === 0 && (
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
