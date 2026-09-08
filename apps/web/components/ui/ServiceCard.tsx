"use client";

import Link from "next/link";

export type ServiceCardProps = {
  href: string;
  icon: string;
  code: string;
  title: string;
  description: string;
  stats?: string;
  audience?: string;
  workflow?: string;
  status?: "available" | "coming_soon" | "upgrade";
  statusLabel?: string;
};

export function ServiceCard({
  href,
  icon,
  code,
  title,
  description,
  stats,
  audience,
  workflow,
  status = "available",
  statusLabel,
}: ServiceCardProps) {
  const isDisabled = status === "coming_soon";

  const card = (
    <div
      className={`group relative flex flex-col rounded-2xl border bg-white p-6 shadow-card transition ${
        isDisabled
          ? "cursor-default border-slate-200 opacity-60"
          : "border-slate-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-card-hover"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-brand-50 text-2xl">
          {icon}
        </div>
        <span className="text-[10px] font-bold tracking-[0.2em] text-ink-500">{code}</span>
      </div>
      <h3 className="mt-4 text-lg font-bold text-ink-900 group-hover:text-brand-700">{title}</h3>
      <p className="mt-2 flex-1 text-sm leading-relaxed text-ink-600">{description}</p>
      {audience && <p className="mt-3 text-xs font-medium text-ink-500">{audience}</p>}
      {workflow && <p className="mt-1 text-xs text-ink-500">{workflow}</p>}
      {stats && <p className="mt-3 text-xs font-medium text-ink-500">{stats}</p>}
      <div className="mt-4 flex items-center justify-between">
        {status === "upgrade" ? (
          <span className="rounded-full bg-gold-50 px-3 py-1 text-xs font-bold text-gold-800">
            {statusLabel || "Upgrade"}
          </span>
        ) : status === "coming_soon" ? (
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-ink-500">
            {statusLabel || "Coming Soon"}
          </span>
        ) : (
          <span className="text-sm font-semibold text-brand-600 transition group-hover:translate-x-0.5 rtl:group-hover:-translate-x-0.5">
            →
          </span>
        )}
      </div>
    </div>
  );

  if (isDisabled) return card;
  return <Link href={href}>{card}</Link>;
}
