"use client";

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate } from "@/lib/format";

type Status = {
  list_type: string;
  loaded: boolean;
  origin: string | null;
  fetched_at: string | null;
  entry_count: number;
};
type Candidate = {
  reference: string | null;
  entity_type: string;
  primary_name: string;
  matched_name: string;
  score: number;
  citizenship: string | null;
  listing_info: string | null;
};
type Result = { list_type: string; match_count: number; candidates: Candidate[] };

const field =
  "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

const LISTS: { key: string; label: string; canRefresh: boolean }[] = [
  { key: "sanctions", label: "DFAT Consolidated List (sanctions)", canRefresh: true },
  { key: "pep", label: "PEP list", canRefresh: false },
];

export function SanctionsPanel() {
  const [statuses, setStatuses] = useState<Record<string, Status>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [screening, setScreening] = useState(false);
  const [results, setResults] = useState<Result[] | null>(null);

  const loadStatuses = useCallback(async () => {
    const next: Record<string, Status> = {};
    for (const { key } of LISTS) {
      const res = await fetch(`/api/sanctions/status?list_type=${key}`, { cache: "no-store" });
      if (res.ok) next[key] = await res.json();
    }
    setStatuses(next);
  }, []);
  useEffect(() => {
    loadStatuses();
  }, [loadStatuses]);

  async function refresh(listType: string) {
    setBusy(listType);
    setErr(null);
    setMsg(null);
    const res = await fetch(`/api/sanctions/refresh?list_type=${listType}`, { method: "POST" });
    const data = await res.json().catch(() => null);
    setBusy(null);
    if (res.ok) {
      setMsg("List refreshed.");
      loadStatuses();
    } else {
      setErr((data && data.detail) || "Could not refresh. Upload the file manually instead.");
    }
  }

  async function upload(e: React.ChangeEvent<HTMLInputElement>, listType: string) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(listType);
    setErr(null);
    setMsg(null);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("list_type", listType);
    const res = await fetch("/api/sanctions/upload", { method: "POST", body: fd });
    const data = await res.json().catch(() => null);
    setBusy(null);
    e.target.value = "";
    if (res.ok) {
      setMsg(`Loaded ${data.entry_count} entries.`);
      loadStatuses();
    } else {
      setErr((data && data.detail) || "Could not load that file.");
    }
  }

  async function screen(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setScreening(true);
    setErr(null);
    const out: Result[] = [];
    for (const { key } of LISTS) {
      if (!statuses[key]?.loaded) continue;
      const res = await fetch("/api/sanctions/screen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: query.trim(), list_type: key }),
      });
      if (res.ok) out.push(await res.json());
    }
    setScreening(false);
    setResults(out);
  }

  const anyLoaded = LISTS.some((l) => statuses[l.key]?.loaded);

  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="space-y-4 p-5 text-sm">
        {LISTS.map(({ key, label, canRefresh }) => {
          const s = statuses[key];
          return (
            <div key={key} className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-neutral-200">{label}</p>
                <p className="text-xs text-neutral-500">
                  {s?.loaded
                    ? `${s.entry_count} entries - loaded ${formatDate(s.fetched_at)}`
                    : "Not loaded yet."}
                </p>
              </div>
              <div className="flex items-center gap-3">
                {canRefresh && (
                  <Button size="sm" variant="outline" disabled={busy === key} onClick={() => refresh(key)}>
                    {busy === key ? "Working..." : "Refresh"}
                  </Button>
                )}
                <input
                  type="file"
                  accept=".xlsx,.csv"
                  onChange={(e) => upload(e, key)}
                  disabled={busy === key}
                  aria-label={`Upload ${label}`}
                  className="text-xs text-neutral-300 file:mr-2 file:rounded file:border-0 file:bg-neutral-800 file:px-2 file:py-1 file:text-neutral-200"
                />
              </div>
            </div>
          );
        })}

        {msg && <p className="text-xs text-emerald-400">{msg}</p>}
        {err && <p className="text-xs text-red-400">{err}</p>}

        <form onSubmit={screen} className="flex items-center gap-2 border-t border-neutral-800 pt-4">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Screen a name against the loaded lists..."
            aria-label="Name to screen"
            className={`${field} flex-1`}
          />
          <Button size="sm" type="submit" disabled={screening || !anyLoaded}>
            {screening ? "Screening..." : "Screen"}
          </Button>
        </form>

        {results &&
          results.map((r) => (
            <div key={r.list_type} className="space-y-1.5">
              <p className="text-xs uppercase tracking-wide text-neutral-500">{r.list_type}</p>
              {r.match_count === 0 ? (
                <p className="text-xs text-emerald-400">No potential matches (screening aid, not a clearance).</p>
              ) : (
                r.candidates.map((c, i) => (
                  <div
                    key={`${r.list_type}-${c.reference ?? c.primary_name}-${i}`}
                    className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-neutral-100">{c.primary_name}</span>
                      <span className="text-amber-300">{Math.round(c.score * 100)}%</span>
                    </div>
                    <p className="text-xs text-neutral-500">
                      {c.entity_type}
                      {c.citizenship ? ` - ${c.citizenship}` : ""}
                      {c.listing_info ? ` - ${c.listing_info}` : ""}
                    </p>
                  </div>
                ))
              )}
            </div>
          ))}
      </CardContent>
    </Card>
  );
}
