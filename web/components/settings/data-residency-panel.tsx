"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type Attestation = {
  data_region: string;
  hosting_provider: string | null;
  cross_border: boolean;
  dpa_in_place: boolean;
  approved_by_name: string | null;
  attested_on: string | null;
  notes: string | null;
  updated_at: string;
};

const field =
  "w-full rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600 disabled:opacity-60";

export function DataResidencyPanel({ isAdmin }: { isAdmin: boolean }) {
  const [dataRegion, setDataRegion] = useState("");
  const [hostingProvider, setHostingProvider] = useState("");
  const [crossBorder, setCrossBorder] = useState(false);
  const [dpa, setDpa] = useState(false);
  const [approvedBy, setApprovedBy] = useState("");
  const [attestedOn, setAttestedOn] = useState("");
  const [notes, setNotes] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const res = await fetch("/api/attestation", { cache: "no-store" });
      if (res.ok) {
        const a: Attestation | null = await res.json().catch(() => null);
        if (a) {
          setDataRegion(a.data_region ?? "");
          setHostingProvider(a.hosting_provider ?? "");
          setCrossBorder(!!a.cross_border);
          setDpa(!!a.dpa_in_place);
          setApprovedBy(a.approved_by_name ?? "");
          setAttestedOn(a.attested_on ?? "");
          setNotes(a.notes ?? "");
        }
      }
      setLoaded(true);
    })();
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!dataRegion.trim()) {
      setErr("Enter the region where your data is hosted.");
      return;
    }
    setSaving(true);
    setErr(null);
    setMsg(null);
    const res = await fetch("/api/attestation", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        data_region: dataRegion.trim(),
        hosting_provider: hostingProvider.trim() || null,
        cross_border: crossBorder,
        dpa_in_place: dpa,
        approved_by_name: approvedBy.trim() || null,
        attested_on: attestedOn || null,
        notes: notes.trim() || null,
      }),
    });
    const data = await res.json().catch(() => null);
    setSaving(false);
    if (res.ok) setMsg("Attestation saved.");
    else setErr((data && data.detail) || "Could not save the attestation.");
  }

  if (!loaded) {
    return (
      <Card className="border-neutral-800 bg-neutral-900/50">
        <CardContent className="p-5 text-sm text-neutral-500">Loading...</CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="space-y-4 p-5 text-sm">
        <p className="text-neutral-400">
          Record where your firm&apos;s data is hosted and the governance sign-off for that
          choice. Onus is designed to run on Australian infrastructure; if any component is
          offshore, complete a cross-border (APP 8) assessment.
        </p>
        <form onSubmit={save} className="space-y-3">
          <div>
            <label htmlFor="dr-region" className="mb-1 block text-xs text-neutral-400">
              Data region
            </label>
            <input
              id="dr-region"
              value={dataRegion}
              onChange={(e) => setDataRegion(e.target.value)}
              disabled={!isAdmin}
              placeholder="e.g. Australia (Sydney)"
              className={field}
            />
          </div>
          <div>
            <label htmlFor="dr-provider" className="mb-1 block text-xs text-neutral-400">
              Hosting provider (optional)
            </label>
            <input
              id="dr-provider"
              value={hostingProvider}
              onChange={(e) => setHostingProvider(e.target.value)}
              disabled={!isAdmin}
              placeholder="e.g. AWS ap-southeast-2"
              className={field}
            />
          </div>
          <div className="flex flex-wrap gap-5">
            <label className="flex items-center gap-2 text-neutral-300">
              <input
                type="checkbox"
                checked={dpa}
                onChange={(e) => setDpa(e.target.checked)}
                disabled={!isAdmin}
              />
              Data-processing agreement in place
            </label>
            <label className="flex items-center gap-2 text-neutral-300">
              <input
                type="checkbox"
                checked={crossBorder}
                onChange={(e) => setCrossBorder(e.target.checked)}
                disabled={!isAdmin}
              />
              Some data is hosted outside Australia
            </label>
          </div>
          {crossBorder && (
            <p className="rounded-md border border-amber-900/50 bg-amber-950/40 px-3 py-2 text-xs text-amber-300">
              Offshore hosting requires a documented APP 8 cross-border assessment and
              sign-off from your firm&apos;s governance.
            </p>
          )}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="dr-approved" className="mb-1 block text-xs text-neutral-400">
                Approved by (governance)
              </label>
              <input
                id="dr-approved"
                value={approvedBy}
                onChange={(e) => setApprovedBy(e.target.value)}
                disabled={!isAdmin}
                placeholder="Name / role"
                className={field}
              />
            </div>
            <div>
              <label htmlFor="dr-date" className="mb-1 block text-xs text-neutral-400">
                Attested on
              </label>
              <input
                id="dr-date"
                type="date"
                value={attestedOn}
                onChange={(e) => setAttestedOn(e.target.value)}
                disabled={!isAdmin}
                className={field}
              />
            </div>
          </div>
          <div>
            <label htmlFor="dr-notes" className="mb-1 block text-xs text-neutral-400">
              Notes (optional)
            </label>
            <textarea
              id="dr-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              disabled={!isAdmin}
              rows={2}
              className={field}
            />
          </div>
          {msg && <p className="text-xs text-emerald-400">{msg}</p>}
          {err && <p className="text-xs text-red-400">{err}</p>}
          {isAdmin ? (
            <Button size="sm" type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save attestation"}
            </Button>
          ) : (
            <p className="text-xs text-neutral-500">Only an admin can record the attestation.</p>
          )}
        </form>
      </CardContent>
    </Card>
  );
}
