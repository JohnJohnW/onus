"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { RiskBadge } from "@/components/dashboard/risk-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export type CatalogueItem = { key: string; label: string; customer?: string | null };
export type ClientListItem = {
  id: string;
  type: string;
  display_name: string;
  risk_rating: string | null;
  cdd_status: string;
  is_pep: boolean;
  sanctions_hit: boolean;
};

const field =
  "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

function cddLabel(s: string): string {
  return s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function ClientsList({
  clients,
  customerTypes,
}: {
  clients: ClientListItem[];
  customerTypes: CatalogueItem[];
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    type: customerTypes[0]?.key ?? "individual",
    display_name: "",
    is_pep: false,
    pep_kind: "foreign",
    sanctions_hit: false,
  });
  const labels = Object.fromEntries(customerTypes.map((c) => [c.key, c.label]));

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!form.display_name.trim()) return;
    setBusy(true);
    const res = await fetch("/api/clients", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        type: form.type,
        display_name: form.display_name.trim(),
        is_pep: form.is_pep,
        pep_kind: form.is_pep ? form.pep_kind : null,
        sanctions_hit: form.sanctions_hit,
      }),
    });
    setBusy(false);
    if (res.ok) {
      setForm({ ...form, display_name: "", is_pep: false, sanctions_hit: false });
      setOpen(false);
      router.refresh();
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Clients &amp; Matters</h1>
          <p className="mt-2 text-sm text-neutral-400">
            Run customer due diligence before you act, and open matters once it passes.
          </p>
        </div>
        <Button size="sm" className="shrink-0" onClick={() => setOpen((v) => !v)}>
          {open ? "Cancel" : "New client"}
        </Button>
      </header>

      {open && (
        <Card className="mb-6 border-neutral-800 bg-neutral-900/50">
          <CardContent className="p-5">
            <form onSubmit={create} className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <input
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  placeholder="Client name"
                  className={field}
                />
                <select
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
                  className={field}
                >
                  {customerTypes.map((c) => (
                    <option key={c.key} value={c.key}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex flex-wrap items-center gap-4 text-sm text-neutral-300">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={form.is_pep}
                    onChange={(e) => setForm({ ...form, is_pep: e.target.checked })}
                  />
                  Politically exposed person
                </label>
                {form.is_pep && (
                  <select
                    value={form.pep_kind}
                    onChange={(e) => setForm({ ...form, pep_kind: e.target.value })}
                    className={field}
                  >
                    <option value="foreign">Foreign</option>
                    <option value="domestic">Domestic</option>
                    <option value="intl_org">International org</option>
                  </select>
                )}
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={form.sanctions_hit}
                    onChange={(e) => setForm({ ...form, sanctions_hit: e.target.checked })}
                  />
                  Sanctions match
                </label>
              </div>
              <Button type="submit" size="sm" disabled={busy || !form.display_name.trim()}>
                {busy ? "Adding..." : "Add client"}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      <Card className="border-neutral-800 bg-neutral-900/50">
        {clients.length === 0 ? (
          <CardContent className="p-6 text-sm text-neutral-400">No clients yet.</CardContent>
        ) : (
          <CardContent className="divide-y divide-neutral-800 p-0">
            {clients.map((c) => (
              <Link
                key={c.id}
                href={`/clients/${c.id}`}
                className="flex items-center justify-between gap-4 px-5 py-4 hover:bg-neutral-900"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm text-neutral-200">
                    {c.display_name}
                    {c.is_pep && (
                      <span className="ml-2 rounded bg-amber-500/15 px-1.5 py-0.5 text-xs text-amber-300">
                        PEP
                      </span>
                    )}
                    {c.sanctions_hit && (
                      <span className="ml-2 rounded bg-red-500/20 px-1.5 py-0.5 text-xs text-red-300">
                        Sanctions
                      </span>
                    )}
                  </p>
                  <p className="mt-0.5 text-xs text-neutral-500">
                    {labels[c.type] ?? c.type} - CDD: {cddLabel(c.cdd_status)}
                  </p>
                </div>
                <div className="shrink-0">
                  <RiskBadge rating={c.risk_rating ?? "unassessed"} />
                </div>
              </Link>
            ))}
          </CardContent>
        )}
      </Card>
    </div>
  );
}
