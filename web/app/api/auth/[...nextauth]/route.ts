import { NextRequest, NextResponse } from "next/server";

import { handlers } from "@/lib/auth";

const { GET: authGet, POST } = handlers;

export { POST };

/**
 * The engine bearer token lives in the encrypted, httpOnly session cookie and is
 * used only server-side (via `auth()` in the API proxies). next-auth's
 * `GET /api/auth/session` endpoint, however, returns the whole session object as
 * JSON to the browser - which would expose that token to any same-origin script
 * (e.g. via XSS). We wrap the GET handler to strip `access_token` from the
 * `/session` response only. Server-side `auth()` is unaffected, so the proxies
 * keep working; the browser just never receives the token.
 */
export async function GET(req: NextRequest) {
  const res = await authGet(req);
  if (new URL(req.url).pathname.endsWith("/session")) {
    const data = await res.clone().json().catch(() => null);
    if (data && typeof data === "object" && "access_token" in data) {
      delete (data as Record<string, unknown>).access_token;
      return NextResponse.json(data, { status: res.status });
    }
  }
  return res;
}
