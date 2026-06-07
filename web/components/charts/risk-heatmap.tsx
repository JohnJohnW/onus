import { Fragment } from "react";

import { SEVERITY, severityOf } from "@/components/ai/severity";
import { cn } from "@/lib/utils";

// Dependency-free risk matrix: AUSTRAC factor categories (rows) x Low/Medium/High (columns),
// each cell the count of factors at that rating, severity-coloured. One glance shows where
// the firm's ML/TF risk concentrates instead of scrolling four lists.
const COLS = ["low", "medium", "high"] as const;

export function RiskHeatmap({ rows }: { rows: { label: string; items: { rating: string }[] }[] }) {
  const count = (items: { rating: string }[], rating: string) =>
    items.filter((i) => severityOf(i.rating) === rating).length;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
        Where your risk concentrates
      </p>
      <div className="grid grid-cols-[minmax(0,1fr)_repeat(3,3rem)] gap-1 text-sm sm:grid-cols-[minmax(0,1fr)_repeat(3,3.5rem)]">
        <div />
        {COLS.map((c) => (
          <div key={c} className="pb-1 text-center text-xs font-medium text-neutral-400">
            {SEVERITY[c].label}
          </div>
        ))}
        {rows.map((row) => (
          <Fragment key={row.label}>
            <div className="flex items-center pr-2 text-neutral-300">{row.label}</div>
            {COLS.map((c) => {
              const n = count(row.items, c);
              return (
                <div
                  key={c}
                  className={cn(
                    "flex h-10 items-center justify-center rounded border text-sm font-semibold",
                    n > 0 ? SEVERITY[c].chip : "border-neutral-800 bg-neutral-950/40 text-neutral-700"
                  )}
                >
                  {n || ""}
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
