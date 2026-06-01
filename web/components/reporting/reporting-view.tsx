"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate } from "@/lib/format";

export type Report = {
  id: string;
  type: string;
  status: string;
  deadline_basis: string | null;
  lpp_claimed: boolean;
  lpp_form_ref: string | null;
  due_at: string | null;
  lodged_at: string | null;
  reference_number: string | null;
  created_at: string;
};
export type RetentionRecord = {
  id: string;
  category: string;
  entity_type: string | null;
  retention_basis: string;
  basis_date: string | null;
  retention_until: string | null;
  immutable: boolean;
  created_at: string;
};

const TYPE_LABELS: Record<string, string> = {
  smr: "Suspicious matter report",
  ttr: "Threshold transaction report",
  ifti: "International funds transfer",
  annual_compliance: "Annual compliance report",
  cross_border_bni: "Cross-border BNI report",
};
const DEADLINE_LABELS: Record<string, string> = {
  smr_tf_24h: "24 hours (terrorism financing)",
  smr_3bd: "3 business days",
  smr_lpp_5bd: "5 business days (LPP)",
  ttr_10bd: "10 business days",
  ifti_10bd: "10 business days",
  annual_3mo: "by 30 September",
};

const field =
  "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

function statusTone(s: string): string {
  if (s === "lodged") return "text-emerald-400";
  if (s === "not_required") return "text-neutral-500";
  if (s === "ready") return "text-sky-400";
  return "text-amber-400";
}

function ReportRow({ report }: { report: Report }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [reference, setReference] = useState("");
  const [lodging, setLodging] = useState(false);

  async function patch(body: unknown) {
    setBusy(true);
    await fetch(`/api/reports/${report.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(false);
    router.refresh();
  }
  async function dismiss() {
    setBusy(true);
    await fetch(`/api/reports/${report.id}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reasonable_grounds: false, reasoning: "No reasonable grounds to report." }),
    });
    setBusy(false);
    router.refresh();
  }

  const active = report.status === "draft" || report.status === "ready";

  return (
    <div className="px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm text-neutral-200">
            {TYPE_LABELS[report.type] ?? report.type}
            {report.lpp_claimed && (
              <span className="ml-2 rounded bg-neutral-800 px-1.5 py-0.5 text-xs text-neutral-400">
                LPP
              </span>
            )}
          </p>
          <p className="mt-0.5 text-xs text-neutral-500">
            {report.due_at && report.status !== "lodged" && (
              <>
                Due {formatDate(report.due_at)}
                {report.deadline_basis && ` · ${DEADLINE_LABELS[report.deadline_basis] ?? ""}`}
              </>
            )}
            {report.status === "lodged" && report.reference_number && (
              <>Lodged · ref {report.reference_number}</>
            )}
          </p>
        </div>
        <span className={`shrink-0 text-xs capitalize ${statusTone(report.status)}`}>
          {report.status.replace(/_/g, " ")}
        </span>
      </div>
      {active && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {report.status === "draft" && (
            <Button size="sm" variant="outline" disabled={busy} onClick={() => patch({ status: "ready" })}>
              Mark ready
            </Button>
          )}
          {lodging ? (
            <>
              <input
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="AUSTRAC reference"
                className={field}
              />
              <Button
                size="sm"
                disabled={busy || !reference.trim()}
                onClick={() => patch({ status: "lodged", reference_number: reference.trim() })}
              >
                Confirm lodged
              </Button>
            </>
          ) : (
            <Button size="sm" disabled={busy} onClick={() => setLodging(true)}>
              Record lodgement
            </Button>
          )}
          <button
            type="button"
            disabled={busy}
            onClick={dismiss}
            className="text-xs text-neutral-500 hover:text-neutral-300"
          >
            Not required
          </button>
        </div>
      )}
    </div>
  );
}

export function ReportingView({
  reports,
  records,
}: {
  reports: Report[];
  records: RetentionRecord[];
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    type: "smr",
    tf: false,
    lpp_claimed: false,
    grounds: "",
    amount: "",
    reporting_period_end: "",
  });

  async function draft(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    const payload: Record<string, unknown> = { type: form.type };
    if (form.type === "smr") {
      payload.tf = form.tf;
      payload.lpp_claimed = form.lpp_claimed;
      payload.payload = { grounds_for_suspicion: form.grounds };
    } else if (form.type === "ttr") {
      payload.amount = form.amount ? Number(form.amount) : undefined;
    } else if (form.type === "annual_compliance") {
      payload.reporting_period_end = form.reporting_period_end || undefined;
    }
    const res = await fetch("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setBusy(false);
    if (res.ok) {
      setForm({ ...form, grounds: "", amount: "", reporting_period_end: "" });
      router.refresh();
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Reporting</h1>
        <p className="mt-2 text-sm text-neutral-400">
          Draft and track your AUSTRAC reports, and keep your records for the required period.
        </p>
      </header>

      <div className="mb-8 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-200">
        <strong className="font-medium">Tipping-off:</strong> never tell a client that a suspicious
        matter report has been, or may be, made (Act s123). These reports are not visible to clients.
      </div>

      {/* Draft a report */}
      <Card className="mb-8 border-neutral-800 bg-neutral-900/50">
        <CardContent className="p-5">
          <form onSubmit={draft} className="space-y-3">
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
              className={`${field} w-full`}
            >
              <option value="smr">Suspicious matter report (SMR)</option>
              <option value="ttr">Threshold transaction report (TTR)</option>
              <option value="ifti">International funds transfer (IFTI)</option>
              <option value="annual_compliance">Annual compliance report</option>
            </select>
            {form.type === "smr" && (
              <>
                <textarea
                  value={form.grounds}
                  onChange={(e) => setForm({ ...form, grounds: e.target.value })}
                  rows={3}
                  placeholder="Grounds for suspicion (required on the report)…"
                  className={`${field} w-full`}
                />
                <div className="flex flex-wrap gap-4 text-sm text-neutral-300">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" checked={form.tf} onChange={(e) => setForm({ ...form, tf: e.target.checked })} />
                    Terrorism financing (24-hour deadline)
                  </label>
                  <label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={form.lpp_claimed}
                      onChange={(e) => setForm({ ...form, lpp_claimed: e.target.checked })}
                    />
                    Legal professional privilege claimed
                  </label>
                </div>
              </>
            )}
            {form.type === "ttr" && (
              <input
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                placeholder="Physical-currency amount (AUD) — must be ≥ 10,000"
                inputMode="decimal"
                className={`${field} w-full`}
              />
            )}
            {form.type === "annual_compliance" && (
              <input
                value={form.reporting_period_end}
                onChange={(e) => setForm({ ...form, reporting_period_end: e.target.value })}
                placeholder="Reporting period end (YYYY-MM-DD, e.g. 2027-06-30)"
                className={`${field} w-full`}
              />
            )}
            <Button type="submit" size="sm" disabled={busy}>
              {busy ? "Drafting…" : "Draft report"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Reports */}
      <section className="mb-8">
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">Reports</h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          {reports.length === 0 ? (
            <CardContent className="p-6 text-sm text-neutral-400">No reports yet.</CardContent>
          ) : (
            <CardContent className="divide-y divide-neutral-800 p-0">
              {reports.map((r) => (
                <ReportRow key={r.id} report={r} />
              ))}
            </CardContent>
          )}
        </Card>
      </section>

      {/* Records */}
      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Records — retention
        </h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          {records.length === 0 ? (
            <CardContent className="p-6 text-sm text-neutral-400">
              Records appear here as you lodge reports and complete CDD. Nothing is ever
              hard-deleted.
            </CardContent>
          ) : (
            <CardContent className="divide-y divide-neutral-800 p-0">
              {records.map((rec) => (
                <div key={rec.id} className="flex items-center justify-between gap-4 px-5 py-3 text-sm">
                  <span className="capitalize text-neutral-200">{rec.category}</span>
                  <span className="text-xs text-neutral-500">
                    {rec.retention_until ? `Keep until ${rec.retention_until}` : "Retention pending"}
                  </span>
                </div>
              ))}
            </CardContent>
          )}
        </Card>
      </section>
    </div>
  );
}
