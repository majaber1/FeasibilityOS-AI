import type { NextRequest } from "next/server";

export const SESSION_COOKIE = "sb_session";

export function backendUrl(path: string) {
  const origin = process.env.BACKEND_API_URL?.replace(/\/$/, "");
  if (!origin) throw new Error("BACKEND_API_URL is not configured");
  return `${origin}/${path.replace(/^\//, "")}`;
}

export function isSafeBrowserMutation(request: NextRequest) {
  if (["GET", "HEAD", "OPTIONS"].includes(request.method)) return true;
  const fetchSite = request.headers.get("sec-fetch-site");
  if (fetchSite === "cross-site") return false;
  const origin = request.headers.get("origin");
  if (!origin) return true;
  if (origin === request.nextUrl.origin) return true;
  const isLoopback = (u: string) => u.includes("localhost") || u.includes("127.0.0.1") || u.includes("0.0.0.0") || u.includes("::1");
  if (isLoopback(origin) && isLoopback(request.nextUrl.origin)) return true;
  return false;
}

export const sessionCookieOptions = {
  httpOnly: true,
  secure: Boolean(process.env.VERCEL),
  sameSite: "lax" as const,
  path: "/",
  maxAge: 60 * 60 * 8,
};
