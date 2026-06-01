import { NextResponse } from "next/server";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

/**
 * Server-side proxy to the FastAPI signup endpoint, so the browser only ever
 * talks to the Next.js origin (no CORS, engine URL stays server-side).
 */
export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid request body." }, { status: 400 });
  }

  const res = await fetch(`${engineUrl}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
