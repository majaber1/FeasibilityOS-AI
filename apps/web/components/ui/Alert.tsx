"use client";

export function Alert({
  tone = "info",
  children,
}: {
  tone?: "info" | "warning" | "danger" | "success";
  children: React.ReactNode;
}) {
  const tones = {
    info: "border-blue-200 bg-blue-50 text-blue-800",
    warning: "border-amber-200 bg-amber-50 text-amber-800",
    danger: "border-red-200 bg-red-50 text-red-800",
    success: "border-emerald-200 bg-emerald-50 text-emerald-800",
  };
  return (
    <div role="alert" className={`rounded-xl border p-4 text-sm ${tones[tone]}`}>
      {children}
    </div>
  );
}

export function LoadingState({ label }: { label: string }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2" aria-label={label}>
      {[0, 1].map((i) => (
        <div key={i} className="h-32 animate-pulse rounded-2xl border border-slate-200 bg-white" />
      ))}
    </div>
  );
}

export function ErrorState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-8 text-center">
      <h2 className="text-lg font-bold text-red-900">{title}</h2>
      <p className="mt-2 text-sm text-red-800">{detail}</p>
    </div>
  );
}
