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

type Finding = { severity: string; title: string; detail: string; action_key?: string };

export type Review = {
  overall_rating: string;
  headline: string;
  findings?: Finding[];
  // Older persisted reviews used a split shape; kept for back-compat rendering.
  drivers?: { factor: string; rating: string; note: string }[];
  recommended_actions?: { title: string; detail: string; priority: string; action_key?: string }[];
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

// Blend the review into a single findings list: every item is an issue AND its fix. Falls back
// to synthesising findings from the old drivers + recommended_actions split if needed.
function blendedFindings(review: Review): Finding[] {
  if (review.findings && review.findings.length > 0) return review.findings;
  return [
    ...(review.drivers ?? []).map((d) => ({ severity: d.rating, title: d.factor, detail: d.note })),
    ...(review.recommended_actions ?? []).map((a) => ({
      severity: a.priority,
      title: a.title,
      detail: a.detail,
      action_key: a.action_key,
    })),
  ];
}

export function ReviewResult({ review }: { review: Review }) {
  const findings = [...blendedFindings(review)].sort(
    (a, b) => SEVERITY_ORDER[severityOf(a.severity)] - SEVERITY_ORDER[severityOf(b.severity)]
  );
  const needAttention = findings.filter((f) => {
    const s = severityOf(f.severity);
    return s === "high" || s === "medium";
  }).length;

  return (
    <AiResultCard title="Review by Onus">
      <VerdictBanner rating={review.overall_rating} headline={review.headline} />

      {findings.length > 0 && (
        <div className="space-y-2">
          <SectionLabel>
            What matters now{needAttention > 0 ? ` - ${needAttention} need attention` : ""}
          </SectionLabel>
          {findings.map((f, i) => (
            <FindingCard
              key={i}
              severity={f.severity}
              title={f.title}
              detail={f.detail}
              action={f.action_key && f.action_key !== "none" ? REVIEW_ACTIONS[f.action_key] : undefined}
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
