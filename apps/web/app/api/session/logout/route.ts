import { NextRequest, NextResponse } from "next/server";
import { isSafeBrowserMutation, SESSION_COOKIE, sessionCookieOptions } from "@/lib/server-auth";

export async function POST(request: NextRequest) {
  if (!isSafeBrowserMutation(request)) return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, "", { ...sessionCookieOptions, maxAge: 0 });
  return response;
}
