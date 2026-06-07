"use client";

import type { AiAction } from "@/components/ai/action-link";
import {
  AiChecklist,
  AiDisclaimer,
  AiResultCard,
  FindingCard,
  SectionLabel,
  VerdictBanner,
} from "@/components/ai/result-card";
import { SEVERITY_ORDER, severityOf } from "@/components/ai/severity";

export type Review = {
  overall_rating: string;
  headline: string;
  drivers: { factor: string; rating: string; note: string }[];
  recommended_actions: { title: string; detail: string; priority: string; action_key?: string }[];
  checks: string[];
  recommendation: string;
};

// Client-owned registry: the engine sends only a symbolic action_key (validated server-side
// against an allow-list); the URL/method lives here, so nothing the model emits is ever fetched.
const REVIEW_ACTIONS: Record<string, AiAction> = {
  approve_assessment: {
    mode: "call",
    label: "Approve assessment",
    endpoint: "/api/risk-assessment/approve",
    method: "POST",
    doneLabel: "Approved",
  },
  rerun_review: {
    mode: "call",
    label: "Re-run review",
    endpoint: "/api/risk-assessment/review",
    method: "POST",
    doneLabel: "Re-run",
  },
  draft_summary: {
    mode: "call",
    label: "Draft summary",
    endpoint: "/api/risk-assessment/draft-summary",
    method: "POST",
    doneLabel: "Drafted",
  },
  update_assessment: { mode: "navigate", label: "Update risk assessment", href: "/risk-profile" },
  review_clients: { mode: "navigate", label: "Review clients", href: "/clients" },
  open_program: { mode: "navigate", label: "Open compliance program", href: "/compliance-program" },
};

function bySeverity(a: { sev?: string }, b: { sev?: string }) {
  return SEVERITY_ORDER[severityOf(a.sev)] - SEVERITY_ORDER[severityOf(b.sev)];
}

export function ReviewResult({ review }: { review: Review }) {
  const drivers = [...review.drivers].sort((a, b) => bySeverity({ sev: a.rating }, { sev: b.rating }));
  const actions = [...review.recommended_actions].sort((a, b) =>
    bySeverity({ sev: a.priority }, { sev: b.priority })
  );
  const needAttention = actions.filter((a) => severityOf(a.priority) !== "low").length;

  return (
    <AiResultCard title="Review by Onus">
      <VerdictBanner rating={review.overall_rating} headline={review.headline} />

      {drivers.length > 0 && (
        <div className="space-y-2">
          <SectionLabel>What is driving the rating</SectionLabel>
          {drivers.map((d, i) => (
            <FindingCard key={i} severity={d.rating} title={d.factor} detail={d.note} />
          ))}
        </div>
      )}

      {actions.length > 0 && (
        <div className="space-y-2">
          <SectionLabel>
            Recommended actions{needAttention > 0 ? ` - ${needAttention} need attention` : ""}
          </SectionLabel>
          {actions.map((a, i) => (
            <FindingCard
              key={i}
              severity={a.priority}
              title={a.title}
              detail={a.detail}
              action={a.action_key && a.action_key !== "none" ? REVIEW_ACTIONS[a.action_key] : undefined}
            />
          ))}
        </div>
      )}

      {review.checks.length > 0 && (
        <div className="space-y-1.5">
          <SectionLabel>Check since last approval</SectionLabel>
          <AiChecklist items={review.checks} />
        </div>
      )}

      <div className="rounded-md border border-neutral-700 bg-neutral-800/40 px-3 py-2">
        <SectionLabel>Recommendation</SectionLabel>
        <p className="mt-0.5 text-neutral-200">{review.recommendation}</p>
      </div>

      <AiDisclaimer>
        A draft from Onus. Approving the assessment discharges the review and reschedules the next one.
      </AiDisclaimer>
    </AiResultCard>
  );
}
