import { Fragment } from "react";

import { SEVERITY, severityOf } from "@/components/ai/severity";
import { cn } from "@/lib/utils";

// Dependency-free risk matrix: AUSTRAC factor categories (rows) x Low/Medium/High (columns),
// each cell the count of factors at that rating, severity-coloured. Hover a cell for detail;
// click a populated cell (or the row label) to jump to those factors below.
const COLS = ["low", "medium", "high"] as const;

type Row = { label: string; anchor?: string; items: { rating: string }[] };

export function RiskHeatmap({ rows }: { rows: Row[] }) {
  const count = (items: { rating: string }[], rating: string) =>
    items.filter((i) => severityOf(i.rating) === rating).length;

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">
        Where your risk concentrates
      </p>
      <p className="mb-3 mt-0.5 text-xs text-neutral-600">
        Hover a cell for detail; click a highlighted cell to jump to those factors.
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
            {row.anchor ? (
              <a
                href={`#${row.anchor}`}
                className="flex items-center pr-2 text-neutral-300 transition hover:text-neutral-100"
              >
                {row.label}
              </a>
            ) : (
              <div className="flex items-center pr-2 text-neutral-300">{row.label}</div>
            )}
            {COLS.map((c) => {
              const n = count(row.items, c);
              const title =
                n > 0
                  ? `${n} ${row.label.toLowerCase()} factor${n === 1 ? "" : "s"} rated ${SEVERITY[c].label} - click to view`
                  : `No ${row.label.toLowerCase()} factors rated ${SEVERITY[c].label}`;
              const base = cn(
                "flex h-10 items-center justify-center rounded border text-sm font-semibold",
                n > 0 ? SEVERITY[c].chip : "border-neutral-800 bg-neutral-950/40 text-neutral-700"
              );
              return n > 0 && row.anchor ? (
                <a key={c} href={`#${row.anchor}`} title={title} className={cn(base, "transition hover:brightness-125")}>
                  {n}
                </a>
              ) : (
                <div key={c} title={title} className={base}>
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
