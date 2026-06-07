"use client";

import { useState, type ReactNode } from "react";

export type Review = {
  overall_rating: string;
  headline: string;
  drivers: { factor: string; rating: string; note: string }[];
  recommended_actions: { title: string; detail: string; priority: string }[];
  checks: string[];
  recommendation: string;
};

const RATING: Record<string, string> = {
  high: "border-red-500/30 bg-red-500/10 text-red-300",
  medium: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  low: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
  unassessed: "border-neutral-600/40 bg-neutral-700/20 text-neutral-300",
};

function Chip({ value }: { value: string }) {
  const cls = RATING[(value || "").toLowerCase()] ?? RATING.unassessed;
  return (
    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${cls}`}>
      {value}
    </span>
  );
}

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-neutral-500">{children}</p>
  );
}

// Renders a structured periodic review (schema-validated JSON from Onus) as interactive UI:
// a rating chip, driver rows, action cards, and a tickable checklist - instead of a text dump.
export function ReviewResult({ review }: { review: Review }) {
  const [done, setDone] = useState<Record<number, boolean>>({});

  return (
    <div className="mt-3 space-y-4 rounded-lg border border-neutral-800 bg-neutral-900 p-4 text-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-neutral-500">Review by Onus</p>
          <p className="mt-1 text-neutral-200">{review.headline}</p>
        </div>
        <Chip value={review.overall_rating} />
      </div>

      {review.drivers.length > 0 && (
        <div>
          <SectionLabel>What is driving the rating</SectionLabel>
          <div className="space-y-1.5">
            {review.drivers.map((d, i) => (
              <div
                key={i}
                className="flex items-start justify-between gap-3 rounded-md border border-neutral-800 bg-neutral-950/40 px-3 py-2"
              >
                <div>
                  <span className="text-neutral-200">{d.factor}</span>
                  <p className="text-xs text-neutral-500">{d.note}</p>
                </div>
                <Chip value={d.rating} />
              </div>
            ))}
          </div>
        </div>
      )}

      {review.recommended_actions.length > 0 && (
        <div>
          <SectionLabel>Recommended actions</SectionLabel>
          <div className="space-y-1.5">
            {review.recommended_actions.map((a, i) => (
              <div key={i} className="rounded-md border border-neutral-800 bg-neutral-950/40 px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-neutral-100">{a.title}</span>
                  <Chip value={a.priority} />
                </div>
                <p className="mt-0.5 text-xs text-neutral-400">{a.detail}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {review.checks.length > 0 && (
        <div>
          <SectionLabel>Check since last approval</SectionLabel>
          <ul className="space-y-1">
            {review.checks.map((c, i) => (
              <li key={i}>
                <label className="flex cursor-pointer items-start gap-2 text-neutral-300">
                  <input
                    type="checkbox"
                    checked={!!done[i]}
                    onChange={() => setDone((s) => ({ ...s, [i]: !s[i] }))}
                    className="mt-0.5 h-3.5 w-3.5 rounded border-neutral-700 bg-neutral-900"
                  />
                  <span className={done[i] ? "text-neutral-500 line-through" : ""}>{c}</span>
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="rounded-md border border-neutral-700 bg-neutral-800/40 px-3 py-2">
        <SectionLabel>Recommendation</SectionLabel>
        <p className="text-neutral-200">{review.recommendation}</p>
      </div>

      <p className="text-xs text-neutral-600">
        A draft from Onus. Approving the assessment discharges the review and reschedules the next
        one.
      </p>
    </div>
  );
}
