/**
 * @jest-environment node
 */

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

import { NextRequest } from "next/server";
import { GET } from "@/app/api/proxy/[...path]/route";

describe("API reverse proxy route", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it("preserves multiple Set-Cookie headers from upstream responses", async () => {
    const upstreamHeaders = new Headers();
    upstreamHeaders.append(
      "set-cookie",
      "refresh_token=jwt_refresh_val; Path=/; HttpOnly; Secure; SameSite=lax"
    );
    upstreamHeaders.append(
      "set-cookie",
      "tradesensei_session=null; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=lax"
    );
    upstreamHeaders.set("location", "https://tss.framas.cloud/auth/callback?token=ott");

    global.fetch = jest.fn().mockResolvedValue(
      new Response(null, {
        status: 302,
        headers: upstreamHeaders,
      })
    );

    const req = new NextRequest(
      "https://tss.framas.cloud/api/proxy/api/v1/auth/oidc/callback?code=abc&state=xyz"
    );
    const res = await GET(req, {
      params: Promise.resolve({ path: ["api", "v1", "auth", "oidc", "callback"] }),
    });

    expect(res.status).toBe(302);
    expect(res.headers.get("location")).toBe(
      "https://tss.framas.cloud/auth/callback?token=ott"
    );
    expect(res.headers.getSetCookie()).toEqual([
      "refresh_token=jwt_refresh_val; Path=/; HttpOnly; Secure; SameSite=lax",
      "tradesensei_session=null; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; HttpOnly; SameSite=lax",
    ]);
  });
});
