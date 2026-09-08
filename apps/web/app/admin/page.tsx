"use client";

import { FormEvent, useEffect, useState } from "react";
import { useLanguage } from "@/components/LanguageProvider";
import {
  createAdminUser, getAdminStats, getToken, listAdminLeads, listAdminUsers, me,
  type AdminLead, type AdminStats, type UserProfile,
} from "@/lib/api";

export default function AdminPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  const [token, setToken] = useState("");
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [leads, setLeads] = useState<AdminLead[]>([]);
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [state, setState] = useState<"loading" | "denied" | "error" | "ready">("loading");
  const [message, setMessage] = useState("");

  async function refresh(auth: string) {
    const [nextStats, nextLeads, nextUsers] = await Promise.all([
      getAdminStats(auth), listAdminLeads(auth), listAdminUsers(auth),
    ]);
    setStats(nextStats); setLeads(nextLeads); setUsers(nextUsers);
  }

  useEffect(() => {
    const auth = getToken();
    if (!auth) { setState("denied"); return; }
    setToken(auth);
    me(auth).then((user) => {
      if (user.role_key !== "admin") throw new Error("forbidden");
      return refresh(auth);
    }).then(() => setState("ready")).catch((error) =>
      setState(error instanceof Error && error.message === "forbidden" ? "denied" : "error"));
  }, []);

  async function createUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      await createAdminUser(token, {
        email: String(form.get("email")), password: String(form.get("password")),
        full_name: String(form.get("full_name") || ""), role_key: String(form.get("role_key")),
        locale: String(form.get("locale")) as "ar" | "en",
      });
      event.currentTarget.reset(); await refresh(token);
      setMessage(ar ? "تم إنشاء المستخدم." : "User created.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Request failed"); }
  }

  if (state === "loading") return <main className="container-page py-16">{ar ? "جارٍ التحميل…" : "Loading…"}</main>;
  if (state === "denied") return <main className="container-page py-16"><h1 className="text-3xl font-bold">{ar ? "غير مصرح" : "Access denied"}</h1><p className="mt-3 text-ink-600">{ar ? "هذه الصفحة لحساب مدير المنصة فقط." : "This page is restricted to platform administrators."}</p></main>;
  if (state === "error" || !stats) return <main className="container-page py-16 text-red-700">{ar ? "تعذر تحميل بيانات الإدارة." : "Unable to load administration data."}</main>;
  const cards = [["users", ar ? "المستخدمون" : "Users"], ["projects", ar ? "المشاريع" : "Projects"], ["studies", ar ? "الدراسات" : "Studies"], ["reports", ar ? "التقارير" : "Reports"], ["ideas", ar ? "الأفكار" : "Ideas"]] as const;
  const input = "rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-200";
  return <main className="min-h-screen bg-slate-50 py-12"><div className="container-page">
    <p className="text-sm font-semibold text-brand-700">SAUDI-BUISNESS</p><h1 className="mt-2 text-3xl font-bold">{ar ? "إدارة المنصة" : "Platform administration"}</h1>
    <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{cards.map(([key,label]) => <div key={key} className="rounded-2xl border bg-white p-6 shadow-card"><p className="text-sm text-ink-600">{label}</p><p className="mt-2 text-4xl font-bold text-brand-700">{stats[key]}</p></div>)}</div>
    <div className="mt-8 grid gap-8 xl:grid-cols-2">
      <section className="rounded-2xl border bg-white p-7 shadow-card"><h2 className="text-xl font-bold">{ar ? "إنشاء مستخدم" : "Create user"}</h2><form onSubmit={createUser} className="mt-4 grid gap-3 sm:grid-cols-2"><input className={input} name="full_name" placeholder={ar ? "الاسم" : "Name"}/><input className={input} name="email" type="email" required placeholder={ar ? "البريد الإلكتروني" : "Email"}/><input className={input} name="password" type="password" required minLength={8} placeholder={ar ? "كلمة مرور قوية" : "Strong password"}/><select className={input} name="role_key" defaultValue="entrepreneur">{["entrepreneur","consultant","investor","franchise_owner","gov_reviewer","admin"].map(role => <option key={role}>{role}</option>)}</select><select className={input} name="locale" defaultValue={locale}><option value="ar">العربية</option><option value="en">English</option></select><button className="rounded-lg bg-brand-700 px-4 py-2 font-semibold text-white hover:bg-brand-800">{ar ? "إنشاء" : "Create"}</button></form>{message && <p role="status" className="mt-3 text-sm text-brand-800">{message}</p>}</section>
      <section className="rounded-2xl border bg-white p-7 shadow-card"><h2 className="text-xl font-bold">{ar ? "المستخدمون" : "Users"}</h2><div className="mt-4 max-h-72 divide-y overflow-auto">{users.map(user => <div key={user.id} className="py-3 text-sm"><p className="font-medium">{user.full_name || user.email}</p><p className="text-ink-600">{user.email} · {user.role_key}</p></div>)}</div></section>
    </div>
    <section className="mt-8 rounded-2xl border bg-white p-7 shadow-card"><h2 className="text-xl font-bold">{ar ? "طلبات التواصل" : "Lead inbox"}</h2><div className="mt-4 overflow-x-auto"><table className="w-full text-start text-sm"><thead><tr className="border-b text-ink-600"><th className="p-3 text-start">{ar ? "الاسم" : "Name"}</th><th className="p-3 text-start">{ar ? "التواصل" : "Contact"}</th><th className="p-3 text-start">{ar ? "الخطة" : "Plan"}</th><th className="p-3 text-start">{ar ? "الحالة" : "Status"}</th></tr></thead><tbody>{leads.map(lead => <tr key={lead.id} className="border-b"><td className="p-3">{lead.full_name}</td><td className="p-3">{lead.email}</td><td className="p-3">{lead.plan}</td><td className="p-3">{lead.status}</td></tr>)}</tbody></table>{!leads.length && <p className="py-5 text-ink-600">{ar ? "لا توجد طلبات بعد." : "No leads yet."}</p>}</div></section>
    <section className="mt-8 rounded-2xl border bg-white p-7 shadow-card"><h2 className="text-xl font-bold">{ar ? "آخر الأنشطة" : "Recent activity"}</h2><div className="mt-4 divide-y">{stats.recent_activity.length ? stats.recent_activity.map(item => <div key={item.id} className="flex justify-between py-3 text-sm"><span>{item.action}</span><span className="text-ink-600">{item.entity} #{item.entity_id}</span></div>) : <p className="py-4 text-ink-600">{ar ? "لا توجد أنشطة بعد." : "No activity yet."}</p>}</div></section>
  </div></main>;
}
