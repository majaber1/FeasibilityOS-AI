import { NextRequest, NextResponse } from "next/server";
import { backendUpstreamHeaders, backendUrl, isSafeBrowserMutation, SESSION_COOKIE } from "@/lib/server-auth";

const HOP_BY_HOP = new Set(["connection", "content-length", "content-encoding", "host", "keep-alive", "transfer-encoding"]);

const PREFIX = "/api/backend/";

async function proxy(request: NextRequest) {
  if (!isSafeBrowserMutation(request)) return NextResponse.json({ detail: "Invalid request origin" }, { status: 403 });
  // Next's [...path] catch-all segments never include a trailing empty
  // segment, so path.join("/") silently drops a trailing slash (e.g.
  // "/api/backend/projects/" -> "projects"). FastAPI's collection routes are
  // defined with a trailing slash and redirect_slashes=False, so that loss
  // 404s every authenticated collection endpoint. Read the raw pathname
  // instead so the trailing slash (or lack of one) survives verbatim.
  const rest = request.nextUrl.pathname.slice(PREFIX.length);
  const target = new URL(backendUrl(rest));
  request.nextUrl.searchParams.forEach((value, key) => target.searchParams.append(key, value));

  // Build upstream headers from scratch. Do not forward inbound Vercel
  // protection headers (they belong to this web deployment, not the AI API).
  const headers = backendUpstreamHeaders();
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (HOP_BY_HOP.has(lower) || lower === "cookie") return;
    if (lower.startsWith("x-vercel-")) return;
    headers.set(key, value);
  });
  const session = request.cookies.get(SESSION_COOKIE)?.value;
  if (session) headers.set("authorization", `Bearer ${session}`);

  const body = ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer();
  const upstream = await fetch(target, { method: request.method, headers, body, cache: "no-store", redirect: "manual" });
  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => { if (!HOP_BY_HOP.has(key.toLowerCase()) && key.toLowerCase() !== "set-cookie") responseHeaders.set(key, value); });
  const response = new NextResponse(await upstream.arrayBuffer(), { status: upstream.status, headers: responseHeaders });
  if (upstream.status === 401 && session) response.cookies.set(SESSION_COOKIE, "", { httpOnly: true, secure: Boolean(process.env.VERCEL), sameSite: "lax", path: "/", maxAge: 0 });
  return response;
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
