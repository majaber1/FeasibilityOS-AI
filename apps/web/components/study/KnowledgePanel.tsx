"use client";

import { useCallback, useEffect, useState } from "react";

type KnowledgeDoc = {
  id: string;
  title: string;
  project_type?: string | null;
  sector?: string | null;
  document_type?: string | null;
  extraction_status?: string | null;
  confidence?: number | null;
  chunk_count?: number;
  original_filename?: string | null;
};

type Props = {
  ar: boolean;
  apiBase?: string;
  getToken: () => string | null;
};

export function KnowledgePanel({ ar, apiBase = "", getToken }: Props) {
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = getToken();
    if (!token) return;
    try {
      const res = await fetch(`${apiBase}/api/v2/knowledge/documents`, {
        headers: { Authorization: `Bearer ${token}` },
        credentials: "same-origin",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDocs(data.documents || []);
    } catch (e: any) {
      setError(e?.message || "Failed to load knowledge documents");
    }
  }, [apiBase, getToken]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onUpload(file: File | null) {
    if (!file) return;
    const token = getToken();
    if (!token) {
      setError(ar ? "يلزم تسجيل الدخول" : "Login required");
      return;
    }
    setBusy(true);
    setError(null);
    setInfo(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("title", file.name.replace(/\.[^.]+$/, ""));
      const res = await fetch(`${apiBase}/api/v2/knowledge/documents`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
        credentials: "same-origin",
      });
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(detail || `HTTP ${res.status}`);
      }
      setInfo(ar ? "تم استيعاب وثيقة المعرفة" : "Knowledge document ingested");
      await load();
    } catch (e: any) {
      setError(e?.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      className="mb-4 rounded-2xl border border-teal-200 bg-teal-50/40 p-4"
      data-testid="knowledge-panel"
    >
      <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-bold text-ink-900">
            {ar ? "طبقة المعرفة" : "Knowledge Intelligence"}
          </h2>
          <p className="mt-1 text-xs text-ink-600">
            {ar
              ? "ارفع دراسات جدوى سابقة (PDF/DOCX/XLSX) لدعم الافتراضات بأدلة قابلة للتتبع — وليست دردشة عامة."
              : "Upload prior feasibility studies (PDF/DOCX/XLSX) to ground assumptions with traceable evidence — not a chatbot."}
          </p>
        </div>
        <label className="cursor-pointer rounded-lg bg-teal-700 px-3 py-2 text-xs font-semibold text-white hover:bg-teal-800">
          {busy ? (ar ? "جارٍ الرفع…" : "Uploading…") : ar ? "رفع وثيقة" : "Upload document"}
          <input
            type="file"
            accept=".pdf,.docx,.xlsx,.xls,.txt"
            className="hidden"
            data-testid="knowledge-upload-input"
            disabled={busy}
            onChange={(e) => void onUpload(e.target.files?.[0] || null)}
          />
        </label>
      </div>

      {error ? (
        <p className="mb-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800" data-testid="knowledge-error">
          {error}
        </p>
      ) : null}
      {info ? (
        <p className="mb-2 rounded-lg border border-teal-200 bg-white px-3 py-2 text-xs text-teal-900" data-testid="knowledge-info">
          {info}
        </p>
      ) : null}

      {docs.length === 0 ? (
        <p className="text-xs text-ink-500" data-testid="knowledge-empty">
          {ar ? "لا توجد وثائق معرفة بعد." : "No knowledge documents yet."}
        </p>
      ) : (
        <ul className="space-y-2" data-testid="knowledge-doc-list">
          {docs.map((d) => (
            <li
              key={d.id}
              className="rounded-xl border border-teal-100 bg-white px-3 py-2 text-xs"
              data-testid={`knowledge-doc-${d.id}`}
            >
              <p className="font-semibold text-ink-900">{d.title}</p>
              <p className="text-ink-500">
                {[d.project_type, d.sector, d.document_type, d.extraction_status]
                  .filter(Boolean)
                  .join(" · ")}
                {typeof d.chunk_count === "number" ? ` · ${d.chunk_count} chunks` : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default KnowledgePanel;
