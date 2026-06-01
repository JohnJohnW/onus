import { NextResponse } from "next/server";

import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

/** Server-side proxy: record a change request against the current risk assessment. */
export async function POST() {
  const session = await auth();
  if (!session?.access_token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(`${engineUrl}/risk-assessment/request-changes`, {
    method: "POST",
    headers: { Authorization: `Bearer ${session.access_token}` },
  });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
