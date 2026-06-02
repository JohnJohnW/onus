"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { formatDate } from "@/lib/format";

type Policy = {
  id: string;
  area_key: string;
  title: string;
  body: string | null;
  status: string;
  obligation_key: string | null;
  act_reference: string | null;
  documented: boolean;
};
type Role = { id: string; role: string; is_active: boolean };
export type Program = {
  id: string;
  status: string;
  version: number;
  documented_at: string | null;
  approved_by_name: string | null;
  approved_by_role: string | null;
  approved_at: string | null;
  next_review_due: string | null;
  risk_assessment_status: string | null;
  documented_count: number;
  total_count: number;
  policies: Policy[];
  roles: Role[];
};

type Trigger = {
  id: string;
  trigger_type: string;
  description: string | null;
  status: string;
  review_required_by: string | null;
};
type Change = {
  id: string;
  entity_type: string;
  change_summary: string;
  trigger: string;
  is_material: boolean;
  documented: boolean;
  due_at: string | null;
  changed_at: string;
};
export type Lifecycle = {
  next_review_due: string | null;
  status: string;
  open_triggers: Trigger[];
  changes: Change[];
};

function humanize(s: string): string {
  return s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function titleize(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function PolicyRow({ policy }: { policy: Policy }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState(policy.body ?? "");
  const [busy, setBusy] = useState(false);

  async function save(markApproved: boolean) {
    setBusy(true);
    await fetch(`/api/program/policies/${policy.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body, status: markApproved ? "approved" : "draft" }),
    });
    setBusy(false);
    setOpen(false);
    router.refresh();
  }

  async function draftWithOnus() {
    setBusy(true);
    const res = await fetch(`/api/program/policies/${policy.id}/draft`, { method: "POST" });
    setBusy(false);
    if (res.ok) {
      const data = await res.json();
      setBody(data.body ?? "");
      router.refresh();
    }
  }

  return (
    <div className="px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm text-neutral-200">{policy.title}</p>
          {policy.act_reference && (
            <p className="mt-0.5 text-xs text-neutral-600">{policy.act_reference}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-3">
          <span
            className={
              policy.status === "approved"
                ? "text-xs text-emerald-400"
                : policy.documented
                  ? "text-xs text-neutral-400"
                  : "text-xs text-amber-400"
            }
          >
            {policy.status === "approved" ? "Approved" : policy.documented ? "Documented" : "Not documented"}
          </span>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="text-xs text-neutral-500 hover:text-neutral-300"
          >
            {open ? "Close" : "Edit"}
          </button>
        </div>
      </div>
      {open && (
        <div className="mt-3 space-y-2">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={4}
            placeholder="Describe the policies, procedures, systems and controls for this obligation..."
            className="w-full rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600"
          />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="ghost" disabled={busy} onClick={draftWithOnus}>
              {busy ? "Drafting..." : "Draft with Onus"}
            </Button>
            <Button size="sm" variant="outline" disabled={busy} onClick={() => save(false)}>
              Save draft
            </Button>
            <Button size="sm" disabled={busy || !body.trim()} onClick={() => save(true)}>
              Save & mark documented
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function LifecycleSection({ lifecycle }: { lifecycle: Lifecycle | null }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [change, setChange] = useState({
    entity_type: "policy",
    change_summary: "",
    trigger: "significant_change",
    is_material: false,
  });
  const [trig, setTrig] = useState({ trigger_type: "significant_change", description: "" });
  const field =
    "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

  if (!lifecycle) return null;

  async function resolveTrigger(id: string) {
    setBusy(true);
    const res = await fetch(`/api/program/triggers/${id}/resolve`, { method: "POST" });
    setBusy(false);
    if (res.ok) router.refresh();
  }

  async function logChange(e: React.FormEvent) {
    e.preventDefault();
    if (!change.change_summary.trim()) return;
    setBusy(true);
    await fetch("/api/program/changes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(change),
    });
    setBusy(false);
    setChange({ ...change, change_summary: "" });
    router.refresh();
  }
  async function flagReview(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    await fetch("/api/program/triggers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(trig),
    });
    setBusy(false);
    setTrig({ ...trig, description: "" });
    router.refresh();
  }

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
        Program lifecycle
      </h2>
      <Card className="border-neutral-800 bg-neutral-900/50">
        <CardContent className="space-y-4 p-5">
          <p className="text-sm text-neutral-300">
            Next review due:{" "}
            <span className="text-neutral-400">
              {lifecycle.next_review_due ? formatDate(lifecycle.next_review_due) : "after approval"}
            </span>{" "}
            - reviewed at least every 3 years and on a trigger.
          </p>

          <div>
            <p className="mb-1 text-xs uppercase tracking-wide text-neutral-500">
              Open review triggers
            </p>
            {lifecycle.open_triggers.length === 0 ? (
              <p className="text-sm text-neutral-500">None.</p>
            ) : (
              <ul className="space-y-1">
                {lifecycle.open_triggers.map((t) => (
                  <li key={t.id} className="flex items-start justify-between gap-3 text-sm text-amber-300">
                    <span>
                      {humanize(t.trigger_type)}
                      {t.description ? <span className="text-neutral-400"> - {t.description}</span> : ""}
                    </span>
                    <button
                      type="button"
                      onClick={() => resolveTrigger(t.id)}
                      disabled={busy}
                      className="shrink-0 text-xs text-neutral-500 hover:text-neutral-200"
                    >
                      Mark resolved
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <p className="mb-1 text-xs uppercase tracking-wide text-neutral-500">Change log</p>
            {lifecycle.changes.length === 0 ? (
              <p className="text-sm text-neutral-500">No changes logged.</p>
            ) : (
              <ul className="divide-y divide-neutral-800">
                {lifecycle.changes.map((c) => (
                  <li key={c.id} className="py-2 text-sm">
                    <span className="text-neutral-200">{c.change_summary}</span>
                    {c.is_material && (
                      <span className="ml-2 rounded bg-amber-500/15 px-1.5 py-0.5 text-xs text-amber-300">
                        Material - needs approval
                      </span>
                    )}
                    <span className="ml-2 text-xs text-neutral-500">
                      {humanize(c.entity_type)} - {humanize(c.trigger)} - {formatDate(c.changed_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <form onSubmit={logChange} className="space-y-2 border-t border-neutral-800 pt-3">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Log a change</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <select
                value={change.entity_type}
                onChange={(e) => setChange({ ...change, entity_type: e.target.value })}
                className={field}
              >
                <option value="policy">Policy</option>
                <option value="risk_assessment">Risk assessment</option>
                <option value="program">Program</option>
              </select>
              <select
                value={change.trigger}
                onChange={(e) => setChange({ ...change, trigger: e.target.value })}
                className={field}
              >
                <option value="significant_change">Significant change</option>
                <option value="austrac_communication">AUSTRAC communication</option>
                <option value="three_year_review">3-year review</option>
                <option value="evaluation_adverse_finding">Evaluation finding</option>
                <option value="other">Other</option>
              </select>
            </div>
            <input
              value={change.change_summary}
              onChange={(e) => setChange({ ...change, change_summary: e.target.value })}
              placeholder="What changed?"
              className={`${field} w-full`}
            />
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-neutral-300">
                <input
                  type="checkbox"
                  checked={change.is_material}
                  onChange={(e) => setChange({ ...change, is_material: e.target.checked })}
                />
                Material (needs senior-manager approval)
              </label>
              <Button type="submit" size="sm" variant="outline" disabled={busy}>
                Log change
              </Button>
            </div>
          </form>

          <form onSubmit={flagReview} className="space-y-2 border-t border-neutral-800 pt-3">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Flag a review trigger</p>
            <div className="grid gap-2 sm:grid-cols-2">
              <select
                value={trig.trigger_type}
                onChange={(e) => setTrig({ ...trig, trigger_type: e.target.value })}
                className={field}
              >
                <option value="significant_change">Significant change</option>
                <option value="austrac_communication">AUSTRAC communication</option>
                <option value="new_service">New designated service</option>
                <option value="new_country">New country dealt with</option>
              </select>
              <input
                value={trig.description}
                onChange={(e) => setTrig({ ...trig, description: e.target.value })}
                placeholder="Describe the trigger"
                className={field}
              />
            </div>
            <Button type="submit" size="sm" variant="outline" disabled={busy}>
              Flag for review
            </Button>
          </form>
        </CardContent>
      </Card>
    </section>
  );
}

export function ProgramView({
  program,
  lifecycle,
}: {
  program: Program;
  lifecycle: Lifecycle | null;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const isApproved = program.status === "approved";
  const underReview = program.status === "under_review";

  async function act(path: string, payload?: unknown) {
    setBusy(true);
    setError("");
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload ? JSON.stringify(payload) : undefined,
    });
    setBusy(false);
    if (res.ok) router.refresh();
    else setError("Something went wrong. Please try again.");
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Compliance Program</h1>
        <p className="mt-2 text-sm text-neutral-400">
          Your AML/CTF program - the risk assessment plus the policies that manage your risks
          and keep you compliant. It must be documented and approved by a senior manager before
          you provide a designated service.
        </p>
      </header>

      {/* Status banner */}
      {isApproved ? (
        <div className="mb-8 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-5">
          <p className="text-sm text-emerald-200">
            Approved by {program.approved_by_name ?? "your senior manager"}
            {program.approved_at && <> on {formatDate(program.approved_at)}</>}.
            {program.next_review_due && (
              <> Next review due {formatDate(program.next_review_due)}.</>
            )}
          </p>
        </div>
      ) : (
        <div className="mb-8 rounded-lg border border-amber-500/30 bg-amber-500/10 p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm text-amber-200">
              {underReview
                ? "Your program is documented and awaiting senior-manager approval."
                : "Document your policies below, then submit the program for senior-manager approval."}
            </p>
            {underReview ? (
              <Button
                size="sm"
                className="shrink-0"
                disabled={busy}
                onClick={() => act("/api/program/approve", { decision_reason: "Reviewed and adequate." })}
              >
                Approve program
              </Button>
            ) : (
              <Button
                size="sm"
                className="shrink-0"
                disabled={busy}
                onClick={() => act("/api/program/submit")}
              >
                Submit for approval
              </Button>
            )}
          </div>
          {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
        </div>
      )}

      {/* Coverage */}
      <Card className="mb-8 border-neutral-800 bg-neutral-900/50">
        <CardContent className="p-5">
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-300">Policy coverage</span>
            <span className="text-neutral-400">
              {program.documented_count} of {program.total_count} documented
            </span>
          </div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-neutral-800">
            <div
              className="h-full rounded-full bg-emerald-500/70"
              style={{
                width: `${
                  program.total_count
                    ? Math.round((program.documented_count / program.total_count) * 100)
                    : 0
                }%`,
              }}
            />
          </div>
        </CardContent>
      </Card>

      {/* Governance */}
      <section className="mb-8">
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Governance roles
        </h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="p-5">
            {program.roles.length === 0 ? (
              <p className="text-sm text-neutral-500">No governance roles assigned yet.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {program.roles.map((r) => (
                  <span
                    key={r.id}
                    className="rounded-full bg-neutral-800 px-3 py-1 text-xs text-neutral-300"
                  >
                    {titleize(r.role)}
                  </span>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* Policies */}
      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          AML/CTF policies
        </h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="divide-y divide-neutral-800 p-0">
            {program.policies.map((p) => (
              <PolicyRow key={p.id} policy={p} />
            ))}
          </CardContent>
        </Card>
      </section>

      <LifecycleSection lifecycle={lifecycle} />
    </div>
  );
}
