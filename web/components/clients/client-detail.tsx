"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import type { CatalogueItem } from "@/components/clients/clients-list";
import { DocumentsSection } from "@/components/clients/documents-section";
import { RiskBadge } from "@/components/dashboard/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type Party = {
  id: string;
  role: string;
  name: string;
  is_individual: boolean;
  bo_basis: string | null;
  ownership_pct: number | null;
  is_pep: boolean;
  pep_kind: string | null;
  sanctions_hit: boolean;
  verified: boolean;
};
type Matter = {
  id: string;
  designated_service_key: string;
  description: string | null;
  status: string;
  cdd_gate_passed: boolean;
  cdd_gate_basis: string | null;
  risk_rating: string | null;
  opened_at: string;
};
type CddCheck = {
  id: string;
  level: string;
  edd_reason: string | null;
  outcome: string;
  created_at: string;
};
type Alert = {
  id: string;
  indicator_key: string;
  indicator_group: string;
  severity: string;
  narrative: string | null;
  status: string;
  smr_report_id: string | null;
};
type ScreenCandidate = {
  primary_name: string;
  matched_name: string;
  score: number;
  entity_type: string;
  citizenship: string | null;
  listing_info: string | null;
};
type ScreenResult = {
  query_name: string;
  match_count: number;
  candidates: ScreenCandidate[];
  noList?: boolean;
  error?: boolean;
};
export type Indicator = { group: string; group_label: string; key: string; label: string };
export type ClientDetail = {
  id: string;
  type: string;
  display_name: string;
  status: string;
  risk_rating: string | null;
  cdd_status: string;
  is_pep: boolean;
  pep_kind: string | null;
  sanctions_hit: boolean;
  adverse_media_hit: boolean;
  source_of_funds: string | null;
  source_of_wealth: string | null;
  parties: Party[];
  matters: Matter[];
  cdd_checks: CddCheck[];
  alerts: Alert[];
};

const field =
  "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

function titleize(s: string): string {
  return s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function ScreenResultView({ result }: { result: ScreenResult }) {
  if (result.error) {
    return (
      <p className="text-xs text-red-400">
        Screening could not be completed. Please try again.
      </p>
    );
  }
  if (result.noList) {
    return (
      <p className="text-xs text-amber-300">
        No sanctions list is loaded. Load the DFAT Consolidated List in Settings, then screen.
      </p>
    );
  }
  if (result.match_count === 0) {
    return (
      <p className="text-xs text-emerald-400">
        No potential matches for &quot;{result.query_name}&quot;. A screening aid, not a clearance -
        recorded for your audit trail.
      </p>
    );
  }
  return (
    <div className="space-y-1.5">
      <p className="text-xs text-amber-300">
        {result.match_count} potential match{result.match_count === 1 ? "" : "es"} - review before proceeding:
      </p>
      {result.candidates.map((c, i) => (
        <div key={`${c.primary_name}-${i}`} className="rounded border border-neutral-800 bg-neutral-900 px-2.5 py-1.5 text-xs">
          <div className="flex items-center justify-between gap-2">
            <span className="text-neutral-100">{c.primary_name}</span>
            <span className="text-amber-300">{Math.round(c.score * 100)}%</span>
          </div>
          <p className="text-neutral-500">
            {c.entity_type}
            {c.citizenship ? ` - ${c.citizenship}` : ""}
          </p>
          {c.listing_info && <p className="mt-0.5 text-neutral-600">{c.listing_info}</p>}
        </div>
      ))}
    </div>
  );
}

function MonitoringSection({
  clientId,
  alerts,
  indicators,
}: {
  clientId: string;
  alerts: Alert[];
  indicators: Indicator[];
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    indicator_key: indicators[0]?.key ?? "",
    severity: "medium",
    narrative: "",
  });
  const labels = Object.fromEntries(indicators.map((i) => [i.key, i.label]));
  const groups: { label: string; items: Indicator[] }[] = [];
  for (const ind of indicators) {
    let g = groups.find((x) => x.label === ind.group_label);
    if (!g) {
      g = { label: ind.group_label, items: [] };
      groups.push(g);
    }
    g.items.push(ind);
  }

  async function post(path: string, body?: unknown) {
    setBusy(true);
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body ?? {}),
    });
    setBusy(false);
    if (res.ok) router.refresh();
  }
  async function raise(e: React.FormEvent) {
    e.preventDefault();
    if (!form.indicator_key) return;
    await post("/api/alerts", {
      client_id: clientId,
      indicator_key: form.indicator_key,
      severity: form.severity,
      narrative: form.narrative || null,
    });
    setForm({ ...form, narrative: "" });
  }

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
        Monitoring &amp; suspicious activity
      </h2>
      <Card className="border-neutral-800 bg-neutral-900/50">
        <CardContent className="p-5">
          {alerts.length === 0 ? (
            <p className="mb-4 text-sm text-neutral-500">No alerts raised.</p>
          ) : (
            <div className="mb-4 divide-y divide-neutral-800">
              {alerts.map((a) => (
                <div key={a.id} className="py-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm text-neutral-200">
                      {a.narrative || labels[a.indicator_key] || a.indicator_key}
                      <span className="ml-2 text-xs text-neutral-500">({a.severity})</span>
                    </p>
                    <span
                      className={
                        a.status === "escalated_to_smr"
                          ? "shrink-0 text-xs text-red-300"
                          : a.status === "dismissed"
                            ? "shrink-0 text-xs text-neutral-500"
                            : "shrink-0 text-xs text-amber-400"
                      }
                    >
                      {a.status.replace(/_/g, " ")}
                    </span>
                  </div>
                  {(a.status === "open" || a.status === "reviewing") && (
                    <div className="mt-1 flex gap-3">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => post(`/api/alerts/${a.id}/escalate`)}
                        className="text-xs text-red-400 hover:text-red-300"
                      >
                        Escalate to SMR
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => post(`/api/alerts/${a.id}/dismiss`)}
                        className="text-xs text-neutral-500 hover:text-neutral-300"
                      >
                        Dismiss
                      </button>
                    </div>
                  )}
                  {a.status === "escalated_to_smr" && (
                    <p className="mt-1 text-xs text-neutral-500">Draft SMR created - see Reporting.</p>
                  )}
                </div>
              ))}
            </div>
          )}
          <form onSubmit={raise} className="space-y-2">
            <div className="grid gap-2 sm:grid-cols-2">
              <select
                value={form.indicator_key}
                onChange={(e) => setForm({ ...form, indicator_key: e.target.value })}
                className={field}
              >
                {groups.map((g) => (
                  <optgroup key={g.label} label={g.label}>
                    {g.items.map((i) => (
                      <option key={i.key} value={i.key}>
                        {i.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <select
                value={form.severity}
                onChange={(e) => setForm({ ...form, severity: e.target.value })}
                className={field}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
            <input
              value={form.narrative}
              onChange={(e) => setForm({ ...form, narrative: e.target.value })}
              placeholder="What did you observe? (optional)"
              className={`${field} w-full`}
            />
            <Button type="submit" size="sm" variant="outline" disabled={busy}>
              Raise alert
            </Button>
          </form>
        </CardContent>
      </Card>
    </section>
  );
}

export function ClientDetailView({
  client,
  services,
  indicators,
}: {
  client: ClientDetail;
  services: CatalogueItem[];
  indicators: Indicator[];
}) {
  const router = useRouter();
  const serviceLabels = Object.fromEntries(services.map((s) => [s.key, s.label]));
  const [busy, setBusy] = useState(false);
  const [party, setParty] = useState({ name: "", bo_basis: "ownership_25pct", is_pep: false, sanctions_hit: false });
  const [matter, setMatter] = useState({ designated_service_key: services[0]?.key ?? "", description: "" });
  const [classifying, setClassifying] = useState(false);
  const [suggestion, setSuggestion] = useState<{
    service_key: string | null;
    service_label: string | null;
    is_designated_service: boolean | null;
    customer: string | null;
    cdd_tier: string | null;
    rationale: string;
  } | null>(null);
  const [clientScreen, setClientScreen] = useState<ScreenResult | null>(null);
  const [clientPep, setClientPep] = useState<ScreenResult | null>(null);
  const [partyScreen, setPartyScreen] = useState<ScreenResult | null>(null);
  const [partyPep, setPartyPep] = useState<ScreenResult | null>(null);
  const [screening, setScreening] = useState<null | "client" | "party">(null);
  const latestCdd = client.cdd_checks[0];

  async function post(path: string, body: unknown) {
    setBusy(true);
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(false);
    if (res.ok) router.refresh();
    return res.ok;
  }

  async function patch(path: string, body: unknown) {
    setBusy(true);
    const res = await fetch(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(false);
    if (res.ok) router.refresh();
    return res.ok;
  }

  async function screenName(
    name: string,
    listType: string,
    subjectType: string,
    subjectId?: string,
  ): Promise<ScreenResult | null> {
    const res = await fetch("/api/sanctions/screen", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name,
        list_type: listType,
        subject_type: subjectType,
        subject_id: subjectId ?? null,
        record: true,
      }),
    });
    if (res.status === 409) return { query_name: name, match_count: 0, candidates: [], noList: true };
    if (!res.ok) return { query_name: name, match_count: 0, candidates: [], error: true };
    return res.json();
  }

  async function screenClient() {
    setScreening("client");
    setClientScreen(null);
    setClientPep(null);
    const [san, pep] = await Promise.all([
      screenName(client.display_name, "sanctions", "client", client.id),
      screenName(client.display_name, "pep", "client", client.id),
    ]);
    setScreening(null);
    setClientScreen(san);
    setClientPep(pep);
  }

  async function screenParty() {
    if (!party.name.trim()) return;
    setScreening("party");
    setPartyScreen(null);
    setPartyPep(null);
    const [san, pep] = await Promise.all([
      screenName(party.name.trim(), "sanctions", "party"),
      screenName(party.name.trim(), "pep", "party"),
    ]);
    setScreening(null);
    setPartyScreen(san);
    setPartyPep(pep);
    setParty((p) => ({
      ...p,
      sanctions_hit: (san?.match_count ?? 0) > 0 ? true : p.sanctions_hit,
      is_pep: (pep?.match_count ?? 0) > 0 ? true : p.is_pep,
    }));
  }

  async function runCdd() {
    await post(`/api/clients/${client.id}/cdd`, { kyc_fields: { captured: true } });
  }

  async function addParty(e: React.FormEvent) {
    e.preventDefault();
    if (!party.name.trim()) return;
    const okRes = await post(`/api/clients/${client.id}/parties`, {
      role: "beneficial_owner",
      name: party.name.trim(),
      bo_basis: party.bo_basis,
      is_pep: party.is_pep,
      pep_kind: party.is_pep ? "foreign" : null,
      sanctions_hit: party.sanctions_hit,
    });
    if (okRes) setParty({ name: "", bo_basis: "ownership_25pct", is_pep: false, sanctions_hit: false });
  }

  async function openMatter(e: React.FormEvent) {
    e.preventDefault();
    if (!matter.designated_service_key) return;
    const okRes = await post("/api/matters", {
      client_id: client.id,
      designated_service_key: matter.designated_service_key,
      description: matter.description || null,
    });
    if (okRes) {
      setMatter({ designated_service_key: services[0]?.key ?? "", description: "" });
      setSuggestion(null);
    }
  }

  async function classifyMatter() {
    if (!matter.description.trim() || classifying) return;
    setClassifying(true);
    setSuggestion(null);
    const res = await fetch("/api/matters/classify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description: matter.description.trim(), client_id: client.id }),
    });
    setClassifying(false);
    if (res.ok) {
      const data = await res.json();
      setSuggestion(data);
      if (data.service_key) setMatter((m) => ({ ...m, designated_service_key: data.service_key }));
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/clients" className="text-xs text-neutral-500 hover:text-neutral-300">
        Back to clients
      </Link>
      <header className="mb-6 mt-2 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{client.display_name}</h1>
          <p className="mt-1 text-sm text-neutral-400">
            {titleize(client.type)}
            {client.is_pep && ` - ${titleize(client.pep_kind ?? "")} PEP`}
          </p>
        </div>
        <RiskBadge rating={client.risk_rating ?? "unassessed"} />
      </header>

      {client.sanctions_hit && (
        <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
          Sanctions match - you must not provide a designated service to this client. CDD is blocked.
        </div>
      )}

      {/* Sanctions screening */}
      <section className="mb-8">
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Sanctions &amp; PEP screening
        </h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="space-y-3 p-5 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-neutral-300">
                Screen &quot;{client.display_name}&quot; against the DFAT sanctions list (Rules s5-3) and
                the PEP list (Rules s5-5).
              </span>
              <Button size="sm" variant="outline" disabled={busy || screening === "client"} onClick={screenClient}>
                {screening === "client" ? "Screening..." : "Screen sanctions & PEP"}
              </Button>
            </div>

            {clientScreen && (
              <div className="space-y-1.5">
                <p className="text-xs uppercase tracking-wide text-neutral-500">Sanctions</p>
                <ScreenResultView result={clientScreen} />
                {!clientScreen.noList && clientScreen.match_count > 0 && !client.sanctions_hit && (
                  <Button
                    size="sm"
                    disabled={busy}
                    onClick={() => patch(`/api/clients/${client.id}`, { sanctions_hit: true })}
                  >
                    Confirm match - block CDD
                  </Button>
                )}
                {client.sanctions_hit && (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => patch(`/api/clients/${client.id}`, { sanctions_hit: false })}
                  >
                    Clear sanctions flag
                  </Button>
                )}
              </div>
            )}

            {clientPep && (
              <div className="space-y-1.5 border-t border-neutral-800 pt-3">
                <p className="text-xs uppercase tracking-wide text-neutral-500">PEP</p>
                <ScreenResultView result={clientPep} />
                {!clientPep.noList && clientPep.match_count > 0 && !client.is_pep && (
                  <Button
                    size="sm"
                    disabled={busy}
                    onClick={() => patch(`/api/clients/${client.id}`, { is_pep: true, pep_kind: "foreign" })}
                  >
                    Confirm PEP (enhanced CDD)
                  </Button>
                )}
                {client.is_pep && (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => patch(`/api/clients/${client.id}`, { is_pep: false, pep_kind: null })}
                  >
                    Clear PEP flag
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* CDD */}
      <section className="mb-8">
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Customer due diligence
        </h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 p-5">
            <div className="text-sm">
              <p className="text-neutral-200">Status: {titleize(client.cdd_status)}</p>
              {latestCdd && (
                <p className="mt-1 text-xs text-neutral-500">
                  {titleize(latestCdd.level)} CDD - {latestCdd.outcome}
                  {latestCdd.edd_reason ? ` - ${latestCdd.edd_reason}` : ""}
                </p>
              )}
            </div>
            <Button size="sm" disabled={busy} onClick={runCdd}>
              {client.cdd_status === "complete" ? "Re-run CDD" : "Run CDD"}
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Beneficial owners / parties */}
      <section className="mb-8">
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Beneficial owners &amp; associated parties
        </h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="p-5">
            {client.parties.length === 0 ? (
              <p className="text-sm text-neutral-500">None recorded.</p>
            ) : (
              <div className="mb-4 divide-y divide-neutral-800">
                {client.parties.map((p) => (
                  <div key={p.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                    <span className="text-neutral-200">
                      {p.name}
                      <span className="ml-2 text-xs text-neutral-500">
                        {titleize(p.role)}
                        {p.bo_basis ? ` - ${titleize(p.bo_basis)}` : ""}
                      </span>
                    </span>
                    <span className="flex gap-1.5">
                      {p.is_pep && (
                        <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-xs text-amber-300">PEP</span>
                      )}
                      {p.sanctions_hit && (
                        <span className="rounded bg-red-500/20 px-1.5 py-0.5 text-xs text-red-300">Sanctions</span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            )}
            <form onSubmit={addParty} className="space-y-2">
              <div className="grid gap-2 sm:grid-cols-2">
                <input
                  value={party.name}
                  onChange={(e) => setParty({ ...party, name: e.target.value })}
                  placeholder="Beneficial owner name"
                  className={field}
                />
                <select
                  value={party.bo_basis}
                  onChange={(e) => setParty({ ...party, bo_basis: e.target.value })}
                  className={field}
                >
                  <option value="ownership_25pct">Owns 25% or more</option>
                  <option value="control">Controls</option>
                  <option value="both">Owns 25% or more &amp; controls</option>
                  <option value="ceo_fallback">CEO (fallback)</option>
                </select>
              </div>
              <div className="flex flex-wrap items-center gap-4 text-sm text-neutral-300">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={party.is_pep}
                    onChange={(e) => setParty({ ...party, is_pep: e.target.checked })}
                  />
                  Foreign PEP
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={party.sanctions_hit}
                    onChange={(e) => setParty({ ...party, sanctions_hit: e.target.checked })}
                  />
                  Sanctions match
                </label>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={busy || screening === "party" || !party.name.trim()}
                  onClick={screenParty}
                >
                  {screening === "party" ? "Screening..." : "Screen name"}
                </Button>
                <Button type="submit" size="sm" variant="outline" disabled={busy || !party.name.trim()}>
                  Add owner
                </Button>
              </div>
              {partyScreen && (
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-wide text-neutral-500">Sanctions</p>
                  <ScreenResultView result={partyScreen} />
                </div>
              )}
              {partyPep && (
                <div className="space-y-1">
                  <p className="text-xs uppercase tracking-wide text-neutral-500">PEP</p>
                  <ScreenResultView result={partyPep} />
                </div>
              )}
            </form>
          </CardContent>
        </Card>
      </section>

      {/* Documents & evidence */}
      <section className="mb-8">
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Documents &amp; evidence
        </h2>
        <DocumentsSection entityType="client" entityId={client.id} />
      </section>

      {/* Matters */}
      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">Matters</h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="p-5">
            {client.matters.length === 0 ? (
              <p className="mb-4 text-sm text-neutral-500">No matters opened.</p>
            ) : (
              <div className="mb-4 divide-y divide-neutral-800">
                {client.matters.map((m) => (
                  <div key={m.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                    <span className="min-w-0 text-neutral-200">
                      {serviceLabels[m.designated_service_key] ?? m.designated_service_key}
                      {m.description ? <span className="text-neutral-500"> - {m.description}</span> : ""}
                    </span>
                    <span
                      className={
                        m.cdd_gate_passed
                          ? "shrink-0 text-xs text-emerald-400"
                          : "shrink-0 text-xs text-amber-400"
                      }
                    >
                      {m.cdd_gate_passed ? "CDD cleared" : "CDD required"}
                    </span>
                  </div>
                ))}
              </div>
            )}
            <form onSubmit={openMatter} className="space-y-2">
              <select
                value={matter.designated_service_key}
                onChange={(e) => setMatter({ ...matter, designated_service_key: e.target.value })}
                className={`${field} w-full`}
              >
                {services.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.label}
                  </option>
                ))}
              </select>
              <input
                value={matter.description}
                onChange={(e) => setMatter({ ...matter, description: e.target.value })}
                placeholder="Describe the matter, then let Onus classify it..."
                className={`${field} w-full`}
              />
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={busy || classifying || !matter.description.trim()}
                  onClick={classifyMatter}
                >
                  {classifying ? "Classifying..." : "Classify with Onus"}
                </Button>
                <Button type="submit" size="sm" disabled={busy}>
                  Open matter
                </Button>
              </div>
              {suggestion && (
                <div className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-xs">
                  {suggestion.service_label ? (
                    <p className="text-neutral-200">
                      Suggested: <span className="text-neutral-100">{suggestion.service_label}</span>
                      {suggestion.cdd_tier ? ` - ${suggestion.cdd_tier} CDD` : ""}
                      {suggestion.customer ? ` - customer: ${suggestion.customer}` : ""}
                    </p>
                  ) : (
                    <p className="text-amber-300">
                      Onus could not identify a designated service - review manually.
                    </p>
                  )}
                  {suggestion.rationale && <p className="mt-1 text-neutral-500">{suggestion.rationale}</p>}
                  <p className="mt-1 text-neutral-600">A suggestion to confirm, not advice - you decide.</p>
                </div>
              )}
              <p className="text-xs text-neutral-600">
                A matter can only be acted on once CDD is complete (Act s28(1)).
              </p>
            </form>
          </CardContent>
        </Card>
      </section>

      <MonitoringSection clientId={client.id} alerts={client.alerts} indicators={indicators} />
    </div>
  );
}
