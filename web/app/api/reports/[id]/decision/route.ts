import { NextResponse } from "next/server";

import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

export async function POST(request: Request, { params }: { params: { id: string } }) {
  const session = await auth();
  if (!session?.access_token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const body = await request.json().catch(() => ({}));
  const res = await fetch(`${engineUrl}/reports/${params.id}/decision`, {
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
