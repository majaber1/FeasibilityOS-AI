// BACKEND_API_URL (server-only, not exposed to the client) must be set in
// any deployed environment; app/api/backend/[...path]/route.ts reads it at
// request time via lib/server-auth.ts#backendUrl. Fail fast at build/start
// on Vercel instead of silently proxying nothing.
if (process.env.VERCEL && !process.env.BACKEND_API_URL) {
  throw new Error("BACKEND_API_URL must be configured for Vercel deployments");
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Docker consumes Next's standalone server; Vercel applies its own output
  // adapter and must retain the normal Next.js build layout.
  output: process.env.VERCEL ? undefined : "standalone",
  // /api/backend/[...path]/route.ts (the secure, cookie-authenticated proxy)
  // is a dynamic catch-all route. Without this, Next.js auto-redirects
  // /api/backend/feasibility/ -> /api/backend/feasibility (308) before that
  // route handler runs, and FastAPI's redirect_slashes=False then rejects
  // the slash-less form -- silently 401/404ing every authenticated
  // collection endpoint (POST /feasibility/, /projects/, /leads/, ...).
  // Disabling Next's own trailing-slash handling lets the request reach the
  // route handler in a single hop, matching FastAPI's canonical
  // trailing-slash routes exactly (see lib/api.ts call sites).
  skipTrailingSlashRedirect: true,
  // NOTE: there is intentionally no rewrites() here. A prior version of this
  // file rewrote /api/backend/:path(.*) directly to BACKEND_API_URL -- but
  // Next.js applies array-form (afterFiles) rewrites BEFORE dynamic routes
  // are matched, so that rewrite silently intercepted every request before
  // the secure session-cookie proxy in app/api/backend/[...path]/route.ts
  // ever ran, forwarding the browser's non-secret "session" placeholder
  // straight to FastAPI instead of swapping in the real HTTP-only cookie
  // JWT. Every authenticated call 401'd. The route handler is the proxy now;
  // do not reintroduce a rewrite for this path.
};

export default nextConfig;
