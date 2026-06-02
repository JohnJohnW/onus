import { NextResponse } from "next/server";

import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.access_token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  // Forward the multipart form (the uploaded file) straight through to the engine.
  const form = await request.formData();
  const res = await fetch(`${engineUrl}/sanctions/upload`, {
    method: "POST",
    headers: { Authorization: `Bearer ${session.access_token}` },
    body: form,
  });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
