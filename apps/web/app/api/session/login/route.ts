import { NextRequest, NextResponse } from "next/server";
import { backendUrl, isSafeBrowserMutation, SESSION_COOKIE, sessionCookieOptions } from "@/lib/server-auth";

export async function POST(request: NextRequest) {
  if (!isSafeBrowserMutation(request)) return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  const body = await request.text();
  const upstream = await fetch(backendUrl("auth/login"), { method: "POST", headers: { "content-type": "application/json", "x-request-id": crypto.randomUUID() }, body, cache: "no-store" });
  const data = await upstream.json().catch(() => ({}));
  if (!upstream.ok || typeof data.access_token !== "string") return NextResponse.json(data, { status: upstream.status });
  const response = NextResponse.json({ access_token: "session", token_type: "cookie" });
  response.cookies.set(SESSION_COOKIE, data.access_token, sessionCookieOptions);
  return response;
}
