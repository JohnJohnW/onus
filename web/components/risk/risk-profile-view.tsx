"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { RiskBadge } from "@/components/dashboard/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate, relativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";

type RiskItem = { id: string; name: string; rating: string; explanation: string };

export type RiskAssessment = {
  id: string;
  status: string;
  overall_rating: string;
  summary: string;
  next_review_due: string | null;
  updated_at: string;
  created_at: string;
  approved_by_name: string | null;
  approved_at: string | null;
  senior_manager_name: string;
  services: RiskItem[];
  client_types: RiskItem[];
  channels: RiskItem[];
  countries: RiskItem[];
};

const INDICATOR: Record<string, { ring: string; dot: string }> = {
  low: { ring: "bg-emerald-500/15", dot: "bg-emerald-500" },
  medium: { ring: "bg-amber-500/15", dot: "bg-amber-500" },
  high: { ring: "bg-red-500/15", dot: "bg-red-500" },
  unassessed: { ring: "bg-neutral-500/15", dot: "bg-neutral-500" },
};

export function RiskProfileView({ assessment }: { assessment: RiskAssessment }) {
  const router = useRouter();
  const isDraft = assessment.status === "draft";
  const [reviewing, setReviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [changeRequested, setChangeRequested] = useState(false);
  const [updateNote, setUpdateNote] = useState(false);

  async function approve() {
    setSubmitting(true);
    setError("");
    const res = await fetch("/api/risk-assessment/approve", { method: "POST" });
    setSubmitting(false);
    if (!res.ok) {
      setError("Could not approve the assessment. Please try again.");
      return;
    }
    setReviewing(false);
    router.refresh();
  }

  async function requestChanges() {
    setSubmitting(true);
    setError("");
    const res = await fetch("/api/risk-assessment/request-changes", { method: "POST" });
    setSubmitting(false);
    if (!res.ok) {
      setError("Could not submit your request. Please try again.");
      return;
    }
    setChangeRequested(true);
    setReviewing(false);
    router.refresh();
  }

  const indicator = INDICATOR[assessment.overall_rating?.toLowerCase()] ?? INDICATOR.unassessed;

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Your Risk Profile</h1>
        <p className="mt-2 text-sm text-neutral-400">
          Last updated {relativeTime(assessment.updated_at)}.
          {assessment.next_review_due && <> Next review due {formatDate(assessment.next_review_due)}.</>}
        </p>
      </header>

      {/* Status banner */}
      {isDraft ? (
        <div className="mb-8 rounded-lg border border-amber-500/30 bg-amber-500/10 p-5">
          {reviewing ? (
            <div>
              <p className="text-sm text-amber-200">
                Review the full assessment below, then approve it or request changes.
              </p>
              {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button size="sm" onClick={approve} disabled={submitting}>
                  {submitting ? "Approving…" : "Approve"}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={submitting}
                  onClick={requestChanges}
                >
                  Request changes
                </Button>
                <Button size="sm" variant="ghost" disabled={submitting} onClick={() => setReviewing(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-4">
              <p className="text-sm text-amber-200">
                Your risk assessment has been generated but not yet approved.{" "}
                {assessment.senior_manager_name} needs to review and approve it.
              </p>
              <Button size="sm" className="shrink-0" onClick={() => setReviewing(true)}>
                Review and approve
              </Button>
            </div>
          )}
          {changeRequested && (
            <p className="mt-3 text-xs text-amber-200/80">
              Your change request has been recorded — Onus will revisit the assessment.
            </p>
          )}
        </div>
      ) : (
        <div className="mb-8 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-5">
          <p className="text-sm text-emerald-200">
            Your risk assessment was approved by{" "}
            {assessment.approved_by_name ?? "your senior manager"}
            {assessment.approved_at && <> on {formatDate(assessment.approved_at)}</>}.
          </p>
        </div>
      )}

      {/* Overall rating card */}
      <Card className="mb-10 border-neutral-800 bg-neutral-900/50">
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <span
              className={cn(
                "inline-flex h-12 w-12 items-center justify-center rounded-full",
                indicator.ring
              )}
            >
              <span className={cn("h-5 w-5 rounded-full", indicator.dot)} />
            </span>
            <div>
              <p className="text-xs uppercase tracking-wide text-neutral-500">Overall risk rating</p>
              <p className="text-2xl font-semibold capitalize text-neutral-100">
                {assessment.overall_rating}
              </p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-relaxed text-neutral-300">{assessment.summary}</p>
          <div className="mt-5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => (isDraft ? setReviewing(true) : setUpdateNote(true))}
            >
              {isDraft ? "Review risk assessment" : "Update risk assessment"}
            </Button>
            {updateNote && !isDraft && (
              <p className="mt-2 text-xs text-neutral-500">
                Re-assessment will be available here soon.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Category cards */}
      <div className="space-y-6">
        <CategoryCard
          title="Services risk"
          items={assessment.services}
          emptyText="No designated services recorded."
        />
        <CategoryCard
          title="Client risk"
          items={assessment.client_types}
          emptyText="No client types recorded."
        />
        <CategoryCard
          title="Delivery channel risk"
          items={assessment.channels}
          emptyText="No delivery channels recorded."
        />
        <CategoryCard
          title="Country risk"
          items={assessment.countries}
          emptyText="Your firm currently has no elevated country risk."
        />
      </div>
    </div>
  );
}

function CategoryCard({
  title,
  items,
  emptyText,
}: {
  title: string;
  items: RiskItem[];
  emptyText: string;
}) {
  return (
    <section>
      <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">{title}</h2>
      <Card className="border-neutral-800 bg-neutral-900/50">
        {items.length === 0 ? (
          <CardContent className="p-5 text-sm text-neutral-400">{emptyText}</CardContent>
        ) : (
          <CardContent className="divide-y divide-neutral-800 p-0">
            {items.map((item) => (
              <div key={item.id} className="flex items-start justify-between gap-4 px-5 py-4">
                <div className="min-w-0">
                  <p className="text-sm text-neutral-200">{item.name}</p>
                  <p className="mt-1 text-sm text-neutral-500">{item.explanation}</p>
                </div>
                <div className="shrink-0">
                  <RiskBadge rating={item.rating} />
                </div>
              </div>
            ))}
          </CardContent>
        )}
      </Card>
    </section>
  );
}
