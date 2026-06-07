"use client";

import { useState, type ReactNode } from "react";

import { ActionLink, type AiAction } from "@/components/ai/action-link";
import { SEVERITY, severityOf } from "@/components/ai/severity";
import { OnusMark } from "@/components/brand/onus-mark";
import { cn } from "@/lib/utils";

// Reusable kit for presenting AI output with clear hierarchy and action linkage.
// Altitudes: VerdictBanner (heaviest) > FindingCard (middle) > AiChecklist / AiDisclaimer (base).

export function AiResultCard({
  title,
  children,
  footer,
}: {
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="mt-3 overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900">
      {title && (
        <div className="flex items-center gap-2 border-b border-neutral-800 px-4 py-2.5">
          <OnusMark className="h-3.5 w-3.5 text-neutral-300" />
          <span className="text-xs font-medium uppercase tracking-wide text-neutral-400">{title}</span>
        </div>
      )}
      <div className="space-y-4 p-4 text-sm">{children}</div>
      {footer && <div className="border-t border-neutral-800 px-4 py-2.5">{footer}</div>}
    </div>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">{children}</p>;
}

// The heaviest element: the eye should land here first.
export function VerdictBanner({
  rating,
  headline,
  sublabel,
}: {
  rating: string;
  headline: string;
  sublabel?: string;
}) {
  const s = SEVERITY[severityOf(rating)];
  return (
    <div className={cn("flex items-start gap-3 rounded-lg border p-3", s.chip)}>
      <span className={cn("mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full", s.ring)}>
        <s.Icon className={cn("h-5 w-5", s.text)} />
      </span>
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase tracking-wide opacity-80">
          {sublabel ?? `Overall: ${s.label}`}
        </p>
        <p className="mt-0.5 text-base font-semibold leading-snug text-neutral-100">{headline}</p>
      </div>
    </div>
  );
}

export function FindingCard({
  severity,
  title,
  detail,
  action,
  meta,
}: {
  severity: string;
  title: string;
  detail?: string;
  action?: AiAction;
  meta?: ReactNode;
}) {
  const sev = severityOf(severity);
  const s = SEVERITY[sev];
  return (
    <div
      className={cn(
        "rounded-md border border-l-2 border-neutral-800 bg-neutral-950/40 px-3 py-2.5",
        s.rail,
        sev === "high" && s.tintBg
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          <s.Icon className={cn("mt-0.5 h-4 w-4 shrink-0", s.text)} />
          <div className="min-w-0">
            <p className="font-medium text-neutral-100">{title}</p>
            {detail && <p className="mt-0.5 text-xs text-neutral-400">{detail}</p>}
            {meta}
          </div>
        </div>
        <span className={cn("shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium capitalize", s.chip)}>
          {s.label}
        </span>
      </div>
      {action && (
        <div className="mt-2 pl-6">
          <ActionLink action={action} />
        </div>
      )}
    </div>
  );
}

export function AiChecklist({ items }: { items: string[] }) {
  const [done, setDone] = useState<Record<number, boolean>>({});
  return (
    <ul className="space-y-1">
      {items.map((c, i) => (
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
  );
}

export function AiDisclaimer({ children }: { children: ReactNode }) {
  return <p className="text-xs text-neutral-600">{children}</p>;
}
