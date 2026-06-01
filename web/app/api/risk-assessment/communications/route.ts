import { NextResponse } from "next/server";

import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

export async function GET() {
  const session = await auth();
  if (!session?.access_token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(`${engineUrl}/risk-assessment/communications`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ([]));
  return NextResponse.json(data, { status: res.status });
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.access_token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const body = await request.json().catch(() => ({}));
  const res = await fetch(`${engineUrl}/risk-assessment/communications`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
