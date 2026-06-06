import { NextResponse } from "next/server";

import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

export async function GET(_request: Request, { params }: { params: { sessionId: string } }) {
  const session = await auth();
  if (!session?.access_token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(
    `${engineUrl}/risk-assessment/agent-review/${params.sessionId}`,
    { headers: { Authorization: `Bearer ${session.access_token}` }, cache: "no-store" },
  );
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
