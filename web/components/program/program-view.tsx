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
            placeholder="Describe the policies, procedures, systems and controls for this obligation…"
            className="w-full rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600"
          />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="ghost" disabled={busy} onClick={draftWithOnus}>
              {busy ? "Drafting…" : "✨ Draft with Onus"}
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

export function ProgramView({ program }: { program: Program }) {
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
          Your AML/CTF program — the risk assessment plus the policies that manage your risks
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
    </div>
  );
}
