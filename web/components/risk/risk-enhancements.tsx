"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { RiskBadge } from "@/components/dashboard/risk-badge";
import type { CountryItem, RiskAssessment } from "@/components/risk/risk-profile-view";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export type Communication = {
  id: string;
  source_label: string;
  communicated_on: string | null;
  relevance_note: string | null;
  change_made: string | null;
  considered_on: string | null;
  reviewer: string | null;
  created_at: string;
};

const field =
  "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

function Section({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="text-xs font-medium uppercase tracking-wide text-neutral-500">{title}</h2>
      {hint && <p className="mt-1 text-xs text-neutral-600">{hint}</p>}
      <div className="mt-3">{children}</div>
    </section>
  );
}

// --- Methodology ---------------------------------------------------------

function MethodologyControl({ assessment }: { assessment: RiskAssessment }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const isMatrix = assessment.methodology === "likelihood_x_impact";

  async function set(methodology: string, complexity: string) {
    setBusy(true);
    await fetch("/api/risk-assessment/methodology", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ methodology, complexity_tier: complexity }),
    });
    setBusy(false);
    router.refresh();
  }

  return (
    <Section
      title="Assessment method"
      hint="Smaller firms can rate impact only; medium-complexity firms rate likelihood × impact (AUSTRAC Step 2)."
    >
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={isMatrix ? "outline" : "default"}
          disabled={busy}
          onClick={() => set("impact_only", "low")}
        >
          Impact-based (simple)
        </Button>
        <Button
          size="sm"
          variant={isMatrix ? "default" : "outline"}
          disabled={busy}
          onClick={() => set("likelihood_x_impact", "medium")}
        >
          Likelihood × Impact
        </Button>
      </div>
    </Section>
  );
}

// --- Country risk editor -------------------------------------------------

type CountryRow = {
  country: string;
  basel_score: string;
  fatf_listed: boolean;
  sanctions_listed: boolean;
  prescribed_foreign_country: boolean;
  tax_haven: boolean;
  terrorism_support: boolean;
  rating?: string;
};

const OVERRIDES: { key: keyof CountryRow; label: string }[] = [
  { key: "fatf_listed", label: "FATF" },
  { key: "sanctions_listed", label: "Sanctions" },
  { key: "prescribed_foreign_country", label: "Prescribed" },
  { key: "tax_haven", label: "Tax haven" },
  { key: "terrorism_support", label: "Terrorism" },
];

function CountryEditor({ countries }: { countries: CountryItem[] }) {
  const router = useRouter();
  const [rows, setRows] = useState<CountryRow[]>(() =>
    countries.map((c) => ({
      country: c.name,
      basel_score: c.basel_score != null ? String(c.basel_score) : "",
      fatf_listed: c.fatf_listed,
      sanctions_listed: c.sanctions_listed,
      prescribed_foreign_country: c.prescribed_foreign_country,
      tax_haven: c.tax_haven,
      terrorism_support: c.terrorism_support,
      rating: c.rating,
    }))
  );
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  function update(i: number, patch: Partial<CountryRow>) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }
  function addRow() {
    setRows((prev) => [
      ...prev,
      {
        country: "",
        basel_score: "",
        fatf_listed: false,
        sanctions_listed: false,
        prescribed_foreign_country: false,
        tax_haven: false,
        terrorism_support: false,
      },
    ]);
  }
  function removeRow(i: number) {
    setRows((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function save() {
    setBusy(true);
    setMessage("");
    const payload = {
      countries: rows
        .filter((r) => r.country.trim())
        .map((r) => ({
          country: r.country.trim(),
          basel_score: r.basel_score.trim() === "" ? null : Number(r.basel_score),
          fatf_listed: r.fatf_listed,
          sanctions_listed: r.sanctions_listed,
          prescribed_foreign_country: r.prescribed_foreign_country,
          tax_haven: r.tax_haven,
          terrorism_support: r.terrorism_support,
        })),
    };
    const res = await fetch("/api/risk-assessment/countries", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setBusy(false);
    if (res.ok) {
      setMessage("Saved.");
      router.refresh();
    } else {
      setMessage("Could not save.");
    }
  }

  return (
    <Section
      title="Country risk"
      hint="A country is rated High if it is FATF-listed, sanctioned, a prescribed foreign country (Iran, DPRK), a tax haven, or linked to terrorism — otherwise its Basel AML Index band applies."
    >
      <Card className="border-neutral-800 bg-neutral-900/50">
        <CardContent className="space-y-3 p-5">
          {rows.length === 0 && (
            <p className="text-sm text-neutral-500">No countries recorded yet.</p>
          )}
          {rows.map((r, i) => (
            <div key={i} className="rounded-md border border-neutral-800 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <input
                  aria-label="Country"
                  value={r.country}
                  onChange={(e) => update(i, { country: e.target.value })}
                  placeholder="Country"
                  className={`${field} min-w-[10rem] flex-1`}
                />
                <input
                  aria-label="Basel AML Index score"
                  value={r.basel_score}
                  onChange={(e) => update(i, { basel_score: e.target.value })}
                  placeholder="Basel score"
                  inputMode="decimal"
                  className={`${field} w-28`}
                />
                {r.rating && <RiskBadge rating={r.rating} />}
                <button
                  type="button"
                  onClick={() => removeRow(i)}
                  className="ml-auto text-xs text-neutral-500 hover:text-neutral-300"
                >
                  Remove
                </button>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {OVERRIDES.map((o) => {
                  const on = r[o.key] as boolean;
                  return (
                    <button
                      key={o.key}
                      type="button"
                      onClick={() => update(i, { [o.key]: !on } as Partial<CountryRow>)}
                      className={
                        on
                          ? "rounded-full bg-red-500/20 px-2.5 py-1 text-xs text-red-300"
                          : "rounded-full bg-neutral-800 px-2.5 py-1 text-xs text-neutral-400 hover:text-neutral-200"
                      }
                    >
                      {o.label}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
          <div className="flex items-center gap-3 pt-1">
            <Button size="sm" variant="outline" onClick={addRow} disabled={busy}>
              Add country
            </Button>
            <Button size="sm" onClick={save} disabled={busy}>
              {busy ? "Saving…" : "Save countries"}
            </Button>
            {message && <span className="text-xs text-neutral-400">{message}</span>}
          </div>
        </CardContent>
      </Card>
    </Section>
  );
}

// --- Proliferation financing --------------------------------------------

const PF_CRITERIA: { key: string; label: string }[] = [
  { key: "australia_only_operations", label: "We operate only in Australia" },
  {
    key: "no_high_risk_jurisdiction_customers",
    label: "No customers located in or connected to high-risk jurisdictions",
  },
  {
    key: "no_value_or_dual_use_goods_movement",
    label: "We don't move money, sensitive or dual-use goods",
  },
  { key: "no_pf_relevant_service", label: "We don't offer a service relevant to proliferation financing" },
];

function PfCard({ assessment }: { assessment: RiskAssessment }) {
  const router = useRouter();
  const [checks, setChecks] = useState<Record<string, boolean>>({
    australia_only_operations: false,
    no_high_risk_jurisdiction_customers: false,
    no_value_or_dual_use_goods_movement: false,
    no_pf_relevant_service: false,
  });
  const [busy, setBusy] = useState(false);

  async function assess() {
    setBusy(true);
    const res = await fetch("/api/risk-assessment/pf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(checks),
    });
    setBusy(false);
    if (res.ok) router.refresh();
  }

  return (
    <Section
      title="Proliferation financing"
      hint="Proliferation financing must be assessed (AUSTRAC Step 2). If all four hold, PF is low and no separate PF policies are required."
    >
      <Card className="border-neutral-800 bg-neutral-900/50">
        <CardContent className="space-y-3 p-5">
          {assessment.pf_assessed && (
            <div className="flex items-center gap-2 text-sm">
              <RiskBadge rating={assessment.pf_risk_rating ?? "unassessed"} />
              <span className="text-neutral-400">{assessment.pf_rationale}</span>
            </div>
          )}
          {PF_CRITERIA.map((c) => (
            <label key={c.key} className="flex items-start gap-2 text-sm text-neutral-300">
              <input
                type="checkbox"
                checked={checks[c.key]}
                onChange={(e) => setChecks((prev) => ({ ...prev, [c.key]: e.target.checked }))}
                className="mt-0.5"
              />
              <span>{c.label}</span>
            </label>
          ))}
          <Button size="sm" onClick={assess} disabled={busy}>
            {busy ? "Assessing…" : "Record PF assessment"}
          </Button>
        </CardContent>
      </Card>
    </Section>
  );
}

// --- AUSTRAC communications register ------------------------------------

function CommunicationsRegister({ initial }: { initial: Communication[] }) {
  const router = useRouter();
  const empty = { source_label: "", communicated_on: "", relevance_note: "", change_made: "" };
  const [form, setForm] = useState(empty);
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!form.source_label.trim()) return;
    setBusy(true);
    const res = await fetch("/api/risk-assessment/communications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setBusy(false);
    if (res.ok) {
      setForm(empty);
      setOpen(false);
      router.refresh();
    }
  }

  return (
    <Section
      title="AUSTRAC communications register"
      hint="Record AUSTRAC communications you've considered. Logging one schedules a review of your assessment (AUSTRAC Step 4)."
    >
      <Card className="border-neutral-800 bg-neutral-900/50">
        <CardContent className="p-0">
          {initial.length === 0 ? (
            <p className="px-5 py-4 text-sm text-neutral-500">No communications logged yet.</p>
          ) : (
            <div className="divide-y divide-neutral-800">
              {initial.map((c) => (
                <div key={c.id} className="px-5 py-4">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm text-neutral-200">{c.source_label}</p>
                    <span className="shrink-0 text-xs text-neutral-500">
                      {c.communicated_on ?? ""}
                    </span>
                  </div>
                  {c.relevance_note && (
                    <p className="mt-1 text-xs text-neutral-500">{c.relevance_note}</p>
                  )}
                  {c.change_made && (
                    <p className="mt-1 text-xs text-neutral-600">Change: {c.change_made}</p>
                  )}
                </div>
              ))}
            </div>
          )}
          <div className="border-t border-neutral-800 p-4">
            {open ? (
              <form onSubmit={add} className="space-y-2">
                <input
                  value={form.source_label}
                  onChange={(e) => setForm({ ...form, source_label: e.target.value })}
                  placeholder="Source (e.g. ML NRA 2024)"
                  className={`${field} w-full`}
                />
                <input
                  value={form.communicated_on}
                  onChange={(e) => setForm({ ...form, communicated_on: e.target.value })}
                  placeholder="Date communicated (YYYY-MM-DD)"
                  className={`${field} w-full`}
                />
                <input
                  value={form.relevance_note}
                  onChange={(e) => setForm({ ...form, relevance_note: e.target.value })}
                  placeholder="Why is it relevant?"
                  className={`${field} w-full`}
                />
                <input
                  value={form.change_made}
                  onChange={(e) => setForm({ ...form, change_made: e.target.value })}
                  placeholder="What changed and how?"
                  className={`${field} w-full`}
                />
                <div className="flex items-center gap-3">
                  <Button type="submit" size="sm" disabled={busy}>
                    {busy ? "Logging…" : "Log communication"}
                  </Button>
                  <button
                    type="button"
                    onClick={() => setOpen(false)}
                    className="text-xs text-neutral-500 hover:text-neutral-300"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
                Log a communication
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </Section>
  );
}

async function exportRiskAssessment() {
  const res = await fetch("/api/risk-assessment/export");
  if (!res.ok) return;
  const { filename, content } = await res.json();
  const blob = new Blob([content ?? ""], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "risk-assessment.md";
  a.click();
  URL.revokeObjectURL(url);
}

export function RiskEnhancements({
  assessment,
  communications,
}: {
  assessment: RiskAssessment;
  communications: Communication[];
}) {
  return (
    <div className="mx-auto max-w-3xl space-y-10 px-6 pb-12">
      <div className="flex justify-end">
        <Button size="sm" variant="outline" onClick={exportRiskAssessment}>
          Export risk assessment
        </Button>
      </div>
      <MethodologyControl assessment={assessment} />
      <CountryEditor countries={assessment.countries} />
      <PfCard assessment={assessment} />
      <CommunicationsRegister initial={communications} />
    </div>
  );
}
