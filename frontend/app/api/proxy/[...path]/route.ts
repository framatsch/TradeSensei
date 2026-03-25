/**
 * Reverse proxy for all backend API calls.
 *
 * Browser clients call `/api/proxy/v1/...` — this handler forwards the request
 * to the internal backend service (`INTERNAL_API_URL`) which is never exposed
 * publicly.  This keeps the backend off the public internet and eliminates the
 * need for CORS configuration.
 *
 * Path mapping:
 *   Browser   →  /api/proxy/v1/auth/register
 *   Proxy     →  http://backend.tradejournal.svc.cluster.local:8000/api/v1/auth/register
 */

import { type NextRequest, NextResponse } from "next/server";

const INTERNAL_API_URL =
  process.env.INTERNAL_API_URL ?? "http://localhost:8000";

/** Headers that must not be forwarded to the upstream backend. */
const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
]);

async function handler(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
): Promise<NextResponse> {
  const { path } = await params;

  // Forward the path segments as-is to the backend.
  // apiClient baseURL is /api/proxy, client calls e.g. /api/v1/auth/register,
  // so Next.js receives path = ["api","v1","auth","register"]
  // → forward to backend as /api/v1/auth/register.
  const backendPath = `/${path.join("/")}`;
  const search = req.nextUrl.search ?? "";
  const targetUrl = `${INTERNAL_API_URL}${backendPath}${search}`;

  // Forward only safe headers
  const forwardHeaders = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      forwardHeaders.set(key, value);
    }
  });

  let body: BodyInit | null = null;
  if (!["GET", "HEAD"].includes(req.method)) {
    body = await req.arrayBuffer();
  }

  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(targetUrl, {
      method: req.method,
      headers: forwardHeaders,
      body,
      // Disable Next.js fetch cache — proxy responses must always be fresh
      cache: "no-store",
    });
  } catch (err) {
    console.error("[proxy] upstream fetch failed", targetUrl, err);
    return NextResponse.json(
      { detail: "Backend unreachable" },
      { status: 502 }
    );
  }

  // Copy response headers, excluding hop-by-hop
  const resHeaders = new Headers();
  upstreamRes.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
      resHeaders.set(key, value);
    }
  });

  const responseBody = await upstreamRes.arrayBuffer();

  return new NextResponse(responseBody, {
    status: upstreamRes.status,
    headers: resHeaders,
  });
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
export const HEAD = handler;
export const OPTIONS = handler;
