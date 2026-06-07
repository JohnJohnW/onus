"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AiDisclaimer, AiResultCard, FindingCard, SectionLabel } from "@/components/ai/result-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Markdown } from "@/components/ui/markdown";
import { Spinner } from "@/components/ui/spinner";
import { formatDate } from "@/lib/format";

type Doc = {
  id: string;
  filename: string;
  content_type: string | null;
  size_bytes: number;
  created_at: string;
};
type Owner = { name: string; ownership_pct: number | null; role: string | null };
type Identity = {
  full_name: string | null;
  date_of_birth: string | null;
  document_type: string | null;
  document_number: string | null;
  expiry: string | null;
  notes: string | null;
};

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentsSection({ entityType, entityId }: { entityType: string; entityId: string }) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [purpose, setPurpose] = useState("summary");
  const [owners, setOwners] = useState<Owner[]>([]);
  const [addingOwners, setAddingOwners] = useState(false);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [recording, setRecording] = useState(false);
  const [sourceOfFunds, setSourceOfFunds] = useState<string | null>(null);
  const [savingSof, setSavingSof] = useState(false);
  const router = useRouter();

  const load = useCallback(async () => {
    const res = await fetch(`/api/documents?entity_type=${entityType}&entity_id=${entityId}`, {
      cache: "no-store",
    });
    if (res.ok) setDocs(await res.json());
  }, [entityType, entityId]);

  useEffect(() => {
    load();
  }, [load]);

  async function upload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setErr(null);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("entity_type", entityType);
    fd.append("entity_id", entityId);
    const res = await fetch("/api/documents", { method: "POST", body: fd });
    setBusy(false);
    e.target.value = "";
    if (res.ok) {
      load();
    } else {
      const d = await res.json().catch(() => null);
      setErr((d && d.detail) || "Upload failed.");
    }
  }

  async function analyzeDoc(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setAnalyzing(true);
    setErr(null);
    setAnalysis(null);
    setOwners([]);
    setIdentity(null);
    setSourceOfFunds(null);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("purpose", purpose);
    const res = await fetch("/api/documents/analyze", { method: "POST", body: fd });
    setAnalyzing(false);
    e.target.value = "";
    if (res.ok) {
      const d = await res.json();
      setAnalysis(d.analysis ?? null);
      setOwners(d.owners ?? []);
      setIdentity(d.identity ?? null);
      setSourceOfFunds(d.source_of_funds ?? null);
    } else {
      const d = await res.json().catch(() => null);
      setErr((d && d.detail) || "Analysis failed.");
    }
  }

  async function addOwners() {
    setAddingOwners(true);
    setErr(null);
    try {
      let failed = 0;
      for (const o of owners) {
        const res = await fetch(`/api/clients/${entityId}/parties`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role: "beneficial_owner",
            name: o.name,
            ownership_pct: o.ownership_pct,
            bo_basis: o.ownership_pct != null && o.ownership_pct >= 25 ? "ownership_25pct" : "control",
            is_pep: false,
            pep_kind: null,
            sanctions_hit: false,
          }),
        });
        if (!res.ok) failed++;
      }
      setOwners([]);
      setAnalysis(null);
      if (failed > 0) {
        setErr(`Could not add ${failed} owner${failed === 1 ? "" : "s"} - please check and retry.`);
      }
      router.refresh();
    } finally {
      setAddingOwners(false);
    }
  }

  async function recordCddFromId() {
    if (!identity) return;
    setRecording(true);
    setErr(null);
    const res = await fetch(`/api/clients/${entityId}/cdd`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kyc_fields: { ...identity, source: "Onus document analysis" } }),
    });
    setRecording(false);
    if (res.ok) {
      setIdentity(null);
      setAnalysis(null);
      router.refresh();
    } else {
      const d = await res.json().catch(() => null);
      setErr((d && d.detail) || "Could not record CDD.");
    }
  }

  async function saveSourceOfFunds() {
    if (!sourceOfFunds) return;
    setSavingSof(true);
    setErr(null);
    const res = await fetch(`/api/clients/${entityId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source_of_funds: sourceOfFunds }),
    });
    setSavingSof(false);
    if (res.ok) {
      setSourceOfFunds(null);
      setAnalysis(null);
      router.refresh();
    } else {
      const d = await res.json().catch(() => null);
      setErr((d && d.detail) || "Could not save source of funds.");
    }
  }

  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="space-y-3 p-5 text-sm">
        {docs.length === 0 ? (
          <p className="text-neutral-500">No documents attached.</p>
        ) : (
          <div className="divide-y divide-neutral-800">
            {docs.map((d) => (
              <div key={d.id} className="flex items-center justify-between gap-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-neutral-200">{d.filename}</p>
                  <p className="text-xs text-neutral-500">
                    {humanSize(d.size_bytes)} - {formatDate(d.created_at)}
                  </p>
                </div>
                <a
                  href={`/api/documents/${d.id}/download`}
                  className="shrink-0 text-xs text-neutral-400 hover:text-neutral-200"
                >
                  Download
                </a>
              </div>
            ))}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-3 border-t border-neutral-800 pt-3">
          <span className="text-xs text-neutral-400">Attach evidence (ID, verification, signed approval):</span>
          <input
            type="file"
            onChange={upload}
            disabled={busy}
            aria-label="Upload a document"
            className="text-xs text-neutral-300 file:mr-2 file:rounded file:border-0 file:bg-neutral-800 file:px-2 file:py-1 file:text-neutral-200"
          />
        </div>
        <div className="border-t border-neutral-800 pt-3">
          <p className="mb-2 text-xs text-neutral-400">
            Analyze a document with Onus - it reads the file and extracts the key details for you to
            review. Sent for analysis only and not stored (PDF or image works best):
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
              className="rounded border border-neutral-800 bg-neutral-900 px-2 py-1 text-xs text-neutral-200"
            >
              <option value="summary">Summarise and flag risks</option>
              <option value="beneficial_owners">Extract beneficial owners</option>
              <option value="identity">Check ID details</option>
              <option value="source_of_funds">Summarise source of funds</option>
            </select>
            <input
              type="file"
              onChange={analyzeDoc}
              disabled={analyzing}
              aria-label="Analyze a document with Onus"
              className="text-xs text-neutral-300 file:mr-2 file:rounded file:border-0 file:bg-neutral-800 file:px-2 file:py-1 file:text-neutral-200"
            />
            {analyzing && (
              <span className="flex items-center gap-1 text-xs text-neutral-500">
                <Spinner /> Reading...
              </span>
            )}
          </div>
          {analysis && (
            <AiResultCard title="Analysis by Onus">
              {owners.length > 0 ? (
                <div className="space-y-2">
                  <SectionLabel>Beneficial owners found</SectionLabel>
                  {owners.map((o, i) => (
                    <FindingCard
                      key={i}
                      severity="info"
                      title={o.name}
                      detail={
                        [o.ownership_pct != null ? `${o.ownership_pct}% ownership` : null, o.role]
                          .filter(Boolean)
                          .join(" - ") || undefined
                      }
                    />
                  ))}
                  {entityType === "client" && (
                    <Button size="sm" variant="outline" onClick={addOwners} disabled={addingOwners}>
                      {addingOwners ? (
                        <>
                          <Spinner className="mr-2" />
                          Adding...
                        </>
                      ) : (
                        `Add ${owners.length} beneficial owner${owners.length === 1 ? "" : "s"} as parties`
                      )}
                    </Button>
                  )}
                </div>
              ) : identity ? (
                <div className="space-y-2">
                  <SectionLabel>Identity details</SectionLabel>
                  <dl className="grid grid-cols-1 gap-y-1 text-xs sm:grid-cols-2 sm:gap-x-4">
                    {(
                      [
                        ["Name", identity.full_name],
                        ["Date of birth", identity.date_of_birth],
                        ["Document", identity.document_type],
                        ["Number", identity.document_number],
                        ["Expiry", identity.expiry],
                      ] as const
                    ).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-2 border-b border-neutral-800/60 py-1">
                        <dt className="text-neutral-500">{k}</dt>
                        <dd className="text-right text-neutral-200">{v || "Not found"}</dd>
                      </div>
                    ))}
                  </dl>
                  {identity.notes && <FindingCard severity="medium" title="Notes" detail={identity.notes} />}
                  {entityType === "client" && (
                    <Button size="sm" variant="outline" onClick={recordCddFromId} disabled={recording}>
                      {recording ? (
                        <>
                          <Spinner className="mr-2" />
                          Recording...
                        </>
                      ) : (
                        "Record CDD with these details"
                      )}
                    </Button>
                  )}
                </div>
              ) : sourceOfFunds ? (
                <div className="space-y-2">
                  <SectionLabel>Source of funds</SectionLabel>
                  <Markdown content={sourceOfFunds} />
                  {entityType === "client" && (
                    <Button size="sm" variant="outline" onClick={saveSourceOfFunds} disabled={savingSof}>
                      {savingSof ? (
                        <>
                          <Spinner className="mr-2" />
                          Saving...
                        </>
                      ) : (
                        "Save as source of funds"
                      )}
                    </Button>
                  )}
                </div>
              ) : (
                <Markdown content={analysis} />
              )}
              <AiDisclaimer>A draft from Onus for you to review and verify - not a determination.</AiDisclaimer>
            </AiResultCard>
          )}
        </div>
        {err && <p className="text-xs text-red-400">{err}</p>}
        <p className="text-xs text-neutral-600">
          PDF, image, or office file up to 20 MB. Retained for the 7-year period.
        </p>
      </CardContent>
    </Card>
  );
}
