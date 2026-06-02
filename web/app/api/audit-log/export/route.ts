import { NextResponse } from "next/server";

import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

// Streams the firm's audit-log CSV from the engine to the browser as a download,
// keeping the bearer token server-side (same proxy pattern as the rest of /api).
export async function GET() {
  const session = await auth();
  if (!session?.access_token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(`${engineUrl}/audit-log/export`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ detail: "Export failed" }, { status: res.status });
  }
  const csv = await res.text();
  return new NextResponse(csv, {
    status: 200,
    headers: {
      "Content-Type": "text/csv",
      "Content-Disposition": "attachment; filename=onus-audit-log.csv",
    },
  });
}
