"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate } from "@/lib/format";

type Status = {
  loaded: boolean;
  source: string | null;
  origin: string | null;
  fetched_at: string | null;
  entry_count: number;
  url_configured: boolean;
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

const field =
  "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

export function SanctionsPanel() {
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [screening, setScreening] = useState(false);
  const [candidates, setCandidates] = useState<Candidate[] | null>(null);

  async function loadStatus() {
    const res = await fetch("/api/sanctions/status", { cache: "no-store" });
    if (res.ok) setStatus(await res.json());
  }
  useEffect(() => {
    loadStatus();
  }, []);

  async function refresh() {
    setBusy(true);
    setErr(null);
    setMsg(null);
    const res = await fetch("/api/sanctions/refresh", { method: "POST" });
    const data = await res.json().catch(() => null);
    setBusy(false);
    if (res.ok) {
      setStatus(data);
      setMsg("List refreshed from DFAT.");
    } else {
      setErr((data && data.detail) || "Could not refresh. Upload the file manually instead.");
    }
  }

  async function upload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setErr(null);
    setMsg(null);
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/api/sanctions/upload", { method: "POST", body: fd });
    const data = await res.json().catch(() => null);
    setBusy(false);
    e.target.value = "";
    if (res.ok) {
      setStatus(data);
      setMsg(`Loaded ${data.entry_count} entries from ${file.name}.`);
    } else {
      setErr((data && data.detail) || "Could not load that file.");
    }
  }

  async function screen(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setScreening(true);
    setErr(null);
    setCandidates(null);
    const res = await fetch("/api/sanctions/screen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: query.trim() }),
    });
    const data = await res.json().catch(() => null);
    setScreening(false);
    if (res.ok) setCandidates(data.candidates ?? []);
    else setErr((data && data.detail) || "Could not screen that name.");
  }

  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="space-y-4 p-5 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-neutral-200">DFAT Consolidated List</p>
            <p className="text-xs text-neutral-500">
              {status?.loaded
                ? `${status.entry_count} entries - loaded ${formatDate(status.fetched_at)}${
                    status.origin ? ` (${status.origin.replace(/_/g, " ")})` : ""
                  }`
                : "No list loaded yet. Refresh from DFAT or upload the file."}
            </p>
          </div>
          <Button size="sm" variant="outline" disabled={busy} onClick={refresh}>
            {busy ? "Working..." : "Refresh from DFAT"}
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs text-neutral-400">Or upload the file (.xlsx / .csv):</span>
          <input
            type="file"
            accept=".xlsx,.csv"
            onChange={upload}
            disabled={busy}
            aria-label="Upload sanctions list file"
            className="text-xs text-neutral-300 file:mr-2 file:rounded file:border-0 file:bg-neutral-800 file:px-2 file:py-1 file:text-neutral-200"
          />
        </div>

        {msg && <p className="text-xs text-emerald-400">{msg}</p>}
        {err && <p className="text-xs text-red-400">{err}</p>}

        <form onSubmit={screen} className="flex items-center gap-2 border-t border-neutral-800 pt-4">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Screen a name against the list..."
            aria-label="Name to screen"
            className={`${field} flex-1`}
          />
          <Button size="sm" type="submit" disabled={screening || !status?.loaded}>
            {screening ? "Screening..." : "Screen"}
          </Button>
        </form>

        {candidates &&
          (candidates.length === 0 ? (
            <p className="text-xs text-emerald-400">
              No potential matches in the current list. This is a screening aid, not a legal
              clearance - record your decision.
            </p>
          ) : (
            <div className="space-y-2">
              <p className="text-xs text-amber-300">
                {candidates.length} potential match{candidates.length === 1 ? "" : "es"} - review each
                before providing the service:
              </p>
              {candidates.map((c, i) => (
                <div
                  key={`${c.reference ?? c.primary_name}-${i}`}
                  className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-neutral-100">{c.primary_name}</span>
                    <span className="text-xs text-amber-300">{Math.round(c.score * 100)}% match</span>
                  </div>
                  <p className="text-xs text-neutral-500">
                    {c.entity_type}
                    {c.citizenship ? ` - ${c.citizenship}` : ""}
                    {c.reference ? ` - ref ${c.reference}` : ""}
                  </p>
                  {c.listing_info && <p className="mt-1 text-xs text-neutral-600">{c.listing_info}</p>}
                </div>
              ))}
            </div>
          ))}
      </CardContent>
    </Card>
  );
}
