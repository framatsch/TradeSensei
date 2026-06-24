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
 * No ENV variables required. The proxy forwards any http/https URL that
 * arrives in the `url` query parameter. The only callers are
 * resolveStorageUrl() and storageUploadUrl() in lib/storageUrl.ts —
 * both of which are server-generated, not user-supplied.
 */

import { type NextRequest, NextResponse } from "next/server";

function parseTarget(req: NextRequest): URL | null {
  const rawUrl = req.nextUrl.searchParams.get("url");
  if (!rawUrl) return null;
  try {
    const parsed = new URL(rawUrl);
    // Only allow http/https — block file://, data://, etc.
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return null;
    return parsed;
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

  return new NextResponse(upstream.status === 200 ? null : await upstream.arrayBuffer(), {
    status: upstream.status,
  });
}
