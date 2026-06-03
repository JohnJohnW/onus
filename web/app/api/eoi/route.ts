import { NextResponse } from "next/server";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

// Public (no auth): demo visitors register interest in a properly AU-hosted deployment.
export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const res = await fetch(`${engineUrl}/eoi`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
