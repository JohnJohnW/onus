import { NextResponse } from "next/server";

import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

/** Server-side proxy for the onboarding wizard - keeps the JWT off the client. */
export async function POST(request: Request) {
  const session = await auth();
  if (!session?.access_token) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }
  const firmId = session.firm_id;
  const { action, data } = await request.json().catch(() => ({ action: "", data: {} }));
  const d = data ?? {};

  let method = "POST";
  let path = "";
  let body: unknown = {};

  switch (action) {
    case "firm_details":
      method = "PATCH";
      path = `/firms/${firmId}`;
      body = {
        abn: d.abn,
        firm_size: d.firm_size,
        practice_areas: d.practice_areas,
        onboarding_step: 1,
      };
      break;
    case "governance":
      path = "/governance/roles";
      body = { onboarding_step: 2 };
      break;
    case "services":
      path = "/risk-assessment/services";
      body = { services: d.services ?? [], onboarding_step: 3 };
      break;
    case "customer_types":
      path = "/risk-assessment/customer-types";
      body = { customer_types: d.customer_types ?? [], onboarding_step: 4 };
      break;
    case "delivery_channels":
      path = "/risk-assessment/delivery-channels";
      body = { channels: d.channels ?? [], onboarding_step: 5 };
      break;
    case "enrolment":
      method = "PATCH";
      path = `/firms/${firmId}`;
      body = {
        enrolment_status: d.enrolment_status,
        austrac_enrolment_number: d.austrac_enrolment_number || null,
        onboarding_step: 6,
      };
      break;
    case "complete":
      path = "/onboarding/complete";
      body = undefined;
      break;
    default:
      return NextResponse.json({ detail: "Unknown action" }, { status: 400 });
  }

  const res = await fetch(`${engineUrl}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  return NextResponse.json(json, { status: res.status });
}
