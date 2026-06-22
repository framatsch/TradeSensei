/*
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

/**
 * Storage proxy — tunnels presigned S3/SeaweedFS requests through the
 * Next.js server so that the storage backend never needs to be publicly
 * exposed.
 *
 * GET  /api/storage-proxy?url=<presigned>   — image download
 * PUT  /api/storage-proxy?url=<presigned>   — file upload
 *
 * Security: the target URL must match one of the configured storage
 * endpoints (STORAGE_ENDPOINT_URL / STORAGE_PUBLIC_URL). This prevents
 * SSRF — an attacker cannot use this proxy to reach arbitrary internal hosts.
 */

import { type NextRequest, NextResponse } from "next/server";

/** Derive the set of allowed hostnames+ports from the configured endpoints. */
function allowedOrigins(): Set<string> {
  // Read env vars at call time (not at module load) so the allowlist reflects
  // the current runtime configuration without requiring a module cache flush.
  const endpoint = process.env.STORAGE_ENDPOINT_URL ?? "http://localhost:8333";
  const publicUrl = process.env.STORAGE_PUBLIC_URL ?? endpoint;

  const origins = new Set<string>();
  for (const raw of [endpoint, publicUrl]) {
    if (!raw) continue;
    try {
      const { hostname, port } = new URL(raw);
      origins.add(port ? `${hostname}:${port}` : hostname);
    } catch {
      // ignore malformed env values
    }
  }
  return origins;
}

function isAllowedStorageUrl(url: URL): boolean {
  const key = url.port ? `${url.hostname}:${url.port}` : url.hostname;
  return allowedOrigins().has(key);
}

function parseTarget(req: NextRequest): URL | null {
  const rawUrl = req.nextUrl.searchParams.get("url");
  if (!rawUrl) return null;
  try {
    return new URL(rawUrl);
  } catch {
    return null;
  }
}

// ── GET — image download ──────────────────────────────────────────────────────

export async function GET(req: NextRequest): Promise<NextResponse> {
  const targetUrl = parseTarget(req);

  if (!targetUrl) {
    return NextResponse.json({ detail: "Missing or invalid url parameter" }, { status: 400 });
  }

  if (!isAllowedStorageUrl(targetUrl)) {
    console.warn("[storage-proxy] GET rejected:", targetUrl.hostname);
    return NextResponse.json({ detail: "URL not allowed" }, { status: 403 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl.toString(), { method: "GET", cache: "no-store" });
  } catch (err) {
    console.error("[storage-proxy] GET failed", targetUrl.toString(), err);
    return NextResponse.json({ detail: "Storage unreachable" }, { status: 502 });
  }

  const body = await upstream.arrayBuffer();
  const contentType = upstream.headers.get("content-type") ?? "application/octet-stream";

  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "content-type": contentType,
      "cache-control": "private, max-age=3600",
    },
  });
}

// ── PUT — file upload ─────────────────────────────────────────────────────────

export async function PUT(req: NextRequest): Promise<NextResponse> {
  const targetUrl = parseTarget(req);

  if (!targetUrl) {
    return NextResponse.json({ detail: "Missing or invalid url parameter" }, { status: 400 });
  }

  if (!isAllowedStorageUrl(targetUrl)) {
    console.warn("[storage-proxy] PUT rejected:", targetUrl.hostname);
    return NextResponse.json({ detail: "URL not allowed" }, { status: 403 });
  }

  const contentType = req.headers.get("content-type") ?? "application/octet-stream";
  const body = await req.arrayBuffer();

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl.toString(), {
      method: "PUT",
      body,
      headers: { "content-type": contentType },
    });
  } catch (err) {
    console.error("[storage-proxy] PUT failed", targetUrl.toString(), err);
    return NextResponse.json({ detail: "Storage unreachable" }, { status: 502 });
  }

  // S3 presigned PUT returns 200 with empty body on success.
  return new NextResponse(upstream.status === 200 ? null : await upstream.arrayBuffer(), {
    status: upstream.status,
  });
}
