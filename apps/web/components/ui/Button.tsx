"use client";

import Link from "next/link";
import type { ButtonHTMLAttributes } from "react";

const variants = {
  primary: "bg-brand-600 text-white shadow-card hover:bg-brand-700",
  secondary: "border border-slate-300 bg-white text-ink-700 hover:border-brand-500",
  gold: "bg-gold-400 text-brand-900 hover:bg-gold-300",
  ghost: "text-ink-700 hover:bg-slate-100",
  danger: "border border-red-200 bg-white text-red-700 hover:bg-red-50",
} as const;

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: keyof typeof variants;
  href?: string;
};

export function Button({ variant = "primary", href, className = "", children, ...props }: ButtonProps) {
  const cls = `inline-flex items-center justify-center rounded-xl px-5 py-3 text-sm font-semibold transition disabled:opacity-50 ${variants[variant]} ${className}`;
  if (href) {
    return (
      <Link href={href} className={cls}>
        {children}
      </Link>
    );
  }
  return (
    <button className={cls} {...props}>
      {children}
    </button>
  );
}
