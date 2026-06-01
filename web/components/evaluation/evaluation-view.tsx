"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type Evaluator = {
  id: string;
  name: string;
  kind: string;
  independence_confirmed: boolean;
  is_compliance_officer: boolean;
  selection_rationale: string | null;
};
type Finding = {
  id: string;
  area: string;
  is_adverse: boolean;
  description: string;
  remediation_action: string | null;
  status: string;
  wont_fix_reason: string | null;
};
export type Evaluation = {
  id: string;
  status: string;
  frequency_months: number | null;
  frequency_rationale: string | null;
  is_first_evaluation: boolean;
  statutory_deadline: string | null;
  scheduled_for: string | null;
  report_received_at: string | null;
  distributed_to_governing_body_at: string | null;
  distributed_to_senior_manager_at: string | null;
  evaluator: Evaluator | null;
  has_report: boolean;
  findings: Finding[];
};
export type EvaluationsData = {
  first_evaluation_deadline: string | null;
  enrolment_known: boolean;
  evaluations: Evaluation[];
};

const field =
  "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

function titleize(s: string): string {
  return s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function useAction() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function run(path: string, method: string, body?: unknown): Promise<boolean> {
    setBusy(true);
    setError("");
    const res = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    setBusy(false);
    if (res.ok) {
      router.refresh();
      return true;
    }
    const data = await res.json().catch(() => ({}));
    setError(data.detail || "Something went wrong.");
    return false;
  }
  return { busy, error, run };
}

function AssignEvaluatorForm({ evalId }: { evalId: string }) {
  const { busy, error, run } = useAction();
  const [form, setForm] = useState({
    name: "",
    kind: "external",
    is_compliance_officer: false,
    independence_confirmed: false,
    selection_rationale: "",
  });
  return (
    <div className="space-y-2">
      <div className="grid gap-2 sm:grid-cols-2">
        <input
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Evaluator name / firm"
          className={field}
        />
        <select
          value={form.kind}
          onChange={(e) => setForm({ ...form, kind: e.target.value })}
          className={field}
        >
          <option value="external">External</option>
          <option value="internal">Internal</option>
        </select>
      </div>
      <input
        value={form.selection_rationale}
        onChange={(e) => setForm({ ...form, selection_rationale: e.target.value })}
        placeholder="Why are they suitable? (sector + AML experience)"
        className={`${field} w-full`}
      />
      <div className="flex flex-wrap gap-4 text-sm text-neutral-300">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.independence_confirmed}
            onChange={(e) => setForm({ ...form, independence_confirmed: e.target.checked })}
          />
          Confirmed independent
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={form.is_compliance_officer}
            onChange={(e) => setForm({ ...form, is_compliance_officer: e.target.checked })}
          />
          Is the compliance officer / team
        </label>
      </div>
      <Button
        size="sm"
        disabled={busy || !form.name.trim()}
        onClick={() => run(`/api/evaluations/${evalId}/evaluator`, "POST", form)}
      >
        Assign evaluator
      </Button>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

type FindingDraft = { area: string; is_adverse: boolean; description: string };

function ReportForm({ evalId }: { evalId: string }) {
  const { busy, error, run } = useAction();
  const [summary, setSummary] = useState("");
  const [findings, setFindings] = useState<FindingDraft[]>([
    { area: "policy", is_adverse: false, description: "" },
  ]);

  function update(i: number, patch: Partial<FindingDraft>) {
    setFindings((prev) => prev.map((f, idx) => (idx === i ? { ...f, ...patch } : f)));
  }

  return (
    <div className="space-y-2">
      <textarea
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
        rows={2}
        placeholder="Summary of the evaluation process and method..."
        className={`${field} w-full`}
      />
      {findings.map((f, i) => (
        <div key={i} className="flex flex-wrap items-center gap-2">
          <select
            value={f.area}
            onChange={(e) => update(i, { area: e.target.value })}
            className={field}
          >
            <option value="risk_assessment">Risk assessment</option>
            <option value="policy">Policy design</option>
            <option value="compliance">Compliance</option>
          </select>
          <input
            value={f.description}
            onChange={(e) => update(i, { description: e.target.value })}
            placeholder="Finding"
            className={`${field} min-w-[12rem] flex-1`}
          />
          <label className="flex items-center gap-1.5 text-xs text-neutral-400">
            <input
              type="checkbox"
              checked={f.is_adverse}
              onChange={(e) => update(i, { is_adverse: e.target.checked })}
            />
            Adverse
          </label>
        </div>
      ))}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => setFindings([...findings, { area: "policy", is_adverse: false, description: "" }])}
        >
          Add finding
        </Button>
        <Button
          size="sm"
          disabled={busy}
          onClick={() =>
            run(`/api/evaluations/${evalId}/report`, "POST", {
              summary_of_process: summary,
              findings: findings.filter((f) => f.description.trim()),
            })
          }
        >
          Submit report
        </Button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

function FindingRow({ finding }: { finding: Finding }) {
  const { busy, error, run } = useAction();
  const [reason, setReason] = useState("");
  const [askReason, setAskReason] = useState(false);

  return (
    <div className="py-2">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-neutral-200">
          {finding.is_adverse && (
            <span className="mr-2 rounded bg-red-500/20 px-1.5 py-0.5 text-xs text-red-300">Adverse</span>
          )}
          {finding.description}
          <span className="ml-2 text-xs text-neutral-500">({titleize(finding.area)})</span>
        </p>
        <span className="shrink-0 text-xs capitalize text-neutral-400">
          {finding.status.replace(/_/g, " ")}
        </span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => run(`/api/evaluations/findings/${finding.id}`, "PATCH", { status: "in_progress" })}
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          In progress
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => run(`/api/evaluations/findings/${finding.id}`, "PATCH", { status: "done" })}
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          Done
        </button>
        {askReason ? (
          <span className="flex items-center gap-1">
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Reason for not fixing"
              className={`${field} text-xs`}
            />
            <button
              type="button"
              disabled={busy || !reason.trim()}
              onClick={() =>
                run(`/api/evaluations/findings/${finding.id}`, "PATCH", {
                  status: "wont_fix",
                  wont_fix_reason: reason.trim(),
                })
              }
              className="text-xs text-amber-400 hover:text-amber-300"
            >
              Save
            </button>
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setAskReason(true)}
            className="text-xs text-neutral-500 hover:text-neutral-300"
          >
            Won&apos;t fix
          </button>
        )}
      </div>
      {finding.wont_fix_reason && (
        <p className="mt-1 text-xs text-neutral-600">Won&apos;t fix: {finding.wont_fix_reason}</p>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  );
}

function EvaluationCard({ ev }: { ev: Evaluation }) {
  const { busy, error, run } = useAction();
  const distributed = ev.distributed_to_governing_body_at && ev.distributed_to_senior_manager_at;
  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="space-y-4 p-5">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-neutral-200">
            {ev.is_first_evaluation ? "First evaluation" : "Evaluation"}
            {ev.statutory_deadline && (
              <span className="ml-2 text-xs text-neutral-500">due by {ev.statutory_deadline}</span>
            )}
          </p>
          <span className="text-xs capitalize text-neutral-400">{ev.status.replace(/_/g, " ")}</span>
        </div>

        {/* Evaluator */}
        <div>
          <p className="mb-1 text-xs uppercase tracking-wide text-neutral-500">Evaluator</p>
          {ev.evaluator ? (
            <p className="text-sm text-neutral-300">
              {ev.evaluator.name} - {titleize(ev.evaluator.kind)}
            </p>
          ) : (
            <AssignEvaluatorForm evalId={ev.id} />
          )}
        </div>

        {/* Report / findings */}
        {ev.evaluator && (
          <div>
            <p className="mb-1 text-xs uppercase tracking-wide text-neutral-500">Report &amp; findings</p>
            {ev.has_report ? (
              <>
                <div className="divide-y divide-neutral-800">
                  {ev.findings.length === 0 ? (
                    <p className="py-2 text-sm text-neutral-500">No findings recorded.</p>
                  ) : (
                    ev.findings.map((f) => <FindingRow key={f.id} finding={f} />)
                  )}
                </div>
                <div className="mt-3 flex items-center gap-3">
                  {distributed ? (
                    <span className="text-xs text-emerald-400">
                      Distributed to governing body + senior manager
                    </span>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={busy}
                      onClick={() => run(`/api/evaluations/${ev.id}/distribute`, "POST")}
                    >
                      Distribute report
                    </Button>
                  )}
                </div>
                {error && <p className="text-xs text-red-400">{error}</p>}
              </>
            ) : (
              <ReportForm evalId={ev.id} />
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ScheduleForm() {
  const { busy, error, run } = useAction();
  const [form, setForm] = useState({ frequency_months: "36", frequency_rationale: "", is_first_evaluation: true });
  return (
    <Card className="mb-8 border-neutral-800 bg-neutral-900/50">
      <CardContent className="space-y-3 p-5">
        <p className="text-sm text-neutral-300">Schedule an evaluation</p>
        <div className="grid gap-2 sm:grid-cols-2">
          <input
            value={form.frequency_months}
            onChange={(e) => setForm({ ...form, frequency_months: e.target.value })}
            placeholder="Frequency (months, <= 36)"
            inputMode="numeric"
            className={field}
          />
          <input
            value={form.frequency_rationale}
            onChange={(e) => setForm({ ...form, frequency_rationale: e.target.value })}
            placeholder="Frequency rationale (size/complexity)"
            className={field}
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-neutral-300">
          <input
            type="checkbox"
            checked={form.is_first_evaluation}
            onChange={(e) => setForm({ ...form, is_first_evaluation: e.target.checked })}
          />
          This is our first evaluation
        </label>
        <Button
          size="sm"
          disabled={busy}
          onClick={() =>
            run("/api/evaluations", "POST", {
              frequency_months: form.frequency_months ? Number(form.frequency_months) : null,
              frequency_rationale: form.frequency_rationale || null,
              is_first_evaluation: form.is_first_evaluation,
            })
          }
        >
          Schedule
        </Button>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </CardContent>
    </Card>
  );
}

export function EvaluationView({ data }: { data: EvaluationsData }) {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Independent Evaluation</h1>
        <p className="mt-2 text-sm text-neutral-400">
          An independent evaluation of your AML/CTF program - separate from your own reviews, by
          someone who isn&apos;t your compliance officer.
        </p>
      </header>

      <div className="mb-8 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
        First evaluation due by <strong>{data.first_evaluation_deadline}</strong>.
        {!data.enrolment_known && (
          <span className="text-amber-200/70">
            {" "}
            (Earliest staggered date - recalculated once your AUSTRAC enrolment number is recorded.)
          </span>
        )}
      </div>

      <ScheduleForm />

      <div className="space-y-4">
        {data.evaluations.length === 0 ? (
          <p className="text-sm text-neutral-500">No evaluations scheduled yet.</p>
        ) : (
          data.evaluations.map((ev) => <EvaluationCard key={ev.id} ev={ev} />)
        )}
      </div>
    </div>
  );
}
