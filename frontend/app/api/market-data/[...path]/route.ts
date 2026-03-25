/**
 * DEPRECATED — this Next.js market-data proxy is no longer used.
 *
 * Market data requests now go through the FastAPI backend proxy at
 * /api/v1/market-data, reached via the existing /api/proxy route handler.
 *
 * This file is kept in place (returning 410 Gone) to prevent accidental
 * re-introduction of the route.  The original implementation had TLS/DNS
 * issues when running inside Docker containers using the undici HTTP stack.
 */

import { NextResponse } from "next/server";

export function GET(): NextResponse {
  return NextResponse.json(
    {
      detail:
        "This proxy endpoint is deprecated. Use /api/proxy/api/v1/market-data instead.",
    },
    { status: 410 },
  );
}
