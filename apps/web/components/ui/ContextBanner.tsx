"use client";

import Link from "next/link";

export function ContextBanner({
  label,
  name,
  href,
}: {
  label: string;
  name: string;
  href?: string;
}) {
  return (
    <div className="rounded-xl border border-brand-200 bg-brand-50 px-5 py-4 text-sm text-brand-800">
      {label} <strong>{name}</strong>
      {href ? (
        <Link href={href} className="ms-3 font-bold underline">
          →
        </Link>
      ) : null}
    </div>
  );
}

export function ImportSource({
  sourceRecord,
  fields,
  lastSync,
  locale,
}: {
  sourceRecord: string;
  fields: string[];
  lastSync?: string | null;
  locale: "ar" | "en";
}) {
  const ar = locale === "ar";
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
      <p className="font-semibold text-ink-800">{ar ? "مصدر الربط" : "Link source"}</p>
      <p className="mt-1 text-ink-600">{sourceRecord}</p>
      <p className="mt-2 text-ink-600">
        {ar ? "الحقول المستوردة:" : "Imported fields:"} {fields.join(", ") || "—"}
      </p>
      <p className="mt-1 text-xs text-ink-500">
        {ar ? "آخر مزامنة:" : "Last synchronized:"} {lastSync ? new Date(lastSync).toLocaleString(ar ? "ar-SA" : "en-SA") : "—"}
      </p>
    </div>
  );
}
