"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const FIRM_SIZES = ["Sole practitioner", "2-5", "6-20", "21-50", "50+"];
const PRACTICE_AREAS = [
  "Conveyancing",
  "Wills and estates",
  "Commercial",
  "Family law",
  "Litigation",
  "Criminal",
];
const SERVICES = [
  "Property transactions",
  "Trust establishment",
  "Company formation",
  "Client funds management",
  "Business sales",
];
const CUSTOMER_TYPES = [
  "Individual people",
  "Small business owners",
  "Large companies",
  "Trusts or family offices",
  "Overseas clients",
  "Government",
];
const CHANNELS = [
  "Face to face always/usually",
  "Face to face sometimes/rarely",
  "Remote often",
  "Remote sometimes",
  "Online platforms yes",
  "Overseas transactions regularly",
  "Overseas transactions sometimes",
];
const ENROLMENT: [string, string][] = [
  ["not_enrolled", "Not yet enrolled"],
  ["in_progress", "Enrolment in progress"],
  ["enrolled", "Enrolled with AUSTRAC"],
];

const STEP_TITLES = [
  "Your firm",
  "Governance",
  "Services you provide",
  "Who your clients are",
  "How you onboard clients",
  "AUSTRAC enrolment",
  "Review & finish",
];

function CheckList({
  options,
  selected,
  onToggle,
}: {
  options: string[];
  selected: string[];
  onToggle: (v: string) => void;
}) {
  return (
    <div className="space-y-2">
      {options.map((opt) => {
        const active = selected.includes(opt);
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onToggle(opt)}
            className={cn(
              "flex w-full items-center gap-3 rounded-md border px-3 py-2.5 text-left text-sm transition-colors",
              active
                ? "border-neutral-500 bg-neutral-800 text-neutral-50"
                : "border-neutral-800 bg-neutral-900/40 text-neutral-300 hover:border-neutral-700"
            )}
          >
            <span
              className={cn(
                "flex h-4 w-4 shrink-0 items-center justify-center rounded border",
                active ? "border-neutral-300 bg-neutral-100 text-neutral-900" : "border-neutral-600"
              )}
            >
              {active && "✓"}
            </span>
            {opt}
          </button>
        );
      })}
    </div>
  );
}

export function OnboardingWizard({ initialStep = 0 }: { initialStep?: number }) {
  const router = useRouter();
  const [step, setStep] = useState(Math.min(Math.max(initialStep, 0), STEP_TITLES.length - 1));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [abn, setAbn] = useState("");
  const [firmSize, setFirmSize] = useState("");
  const [areas, setAreas] = useState<string[]>([]);
  const [services, setServices] = useState<string[]>([]);
  const [customers, setCustomers] = useState<string[]>([]);
  const [channels, setChannels] = useState<string[]>([]);
  const [enrol, setEnrol] = useState("not_enrolled");
  const [austrac, setAustrac] = useState("");

  const toggle = (list: string[], set: (v: string[]) => void, v: string) =>
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  async function post(action: string, data: unknown): Promise<boolean> {
    setBusy(true);
    setError("");
    const res = await fetch("/api/onboarding", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, data }),
    });
    setBusy(false);
    if (!res.ok) {
      const dd = await res.json().catch(() => ({}));
      setError(typeof dd.detail === "string" ? dd.detail : "Something went wrong. Please try again.");
      return false;
    }
    return true;
  }

  async function next() {
    let ok = false;
    if (step === 0) ok = await post("firm_details", { abn, firm_size: firmSize, practice_areas: areas });
    else if (step === 1) ok = await post("governance", {});
    else if (step === 2) ok = await post("services", { services });
    else if (step === 3) ok = await post("customer_types", { customer_types: customers });
    else if (step === 4) ok = await post("delivery_channels", { channels });
    else if (step === 5) ok = await post("enrolment", { enrolment_status: enrol, austrac_enrolment_number: austrac });
    else if (step === 6) {
      ok = await post("complete", {});
      if (ok) {
        router.push("/dashboard");
        router.refresh();
        return;
      }
    }
    if (ok && step < STEP_TITLES.length - 1) setStep((s) => s + 1);
  }

  const field =
    "w-full rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";
  const label = "mb-1 block text-sm text-neutral-400";

  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col justify-center px-6 py-12">
      <div className="mb-8">
        <div className="mb-2 flex items-center justify-between text-xs text-neutral-500">
          <span className="font-semibold tracking-tight text-neutral-300">Onus</span>
          <span>
            Step {step + 1} of {STEP_TITLES.length}
          </span>
        </div>
        <div className="h-1 w-full overflow-hidden rounded bg-neutral-800">
          <div
            className="h-full bg-neutral-100 transition-all"
            style={{ width: `${((step + 1) / STEP_TITLES.length) * 100}%` }}
          />
        </div>
      </div>

      <h1 className="text-xl font-semibold tracking-tight text-neutral-100">{STEP_TITLES[step]}</h1>
      <div className="mt-6 space-y-4">
        {step === 0 && (
          <>
            <div>
              <label htmlFor="abn" className={label}>ABN</label>
              <input id="abn" value={abn} onChange={(e) => setAbn(e.target.value)} className={field} placeholder="11 digits" />
            </div>
            <div>
              <label htmlFor="firmSize" className={label}>Firm size</label>
              <select id="firmSize" value={firmSize} onChange={(e) => setFirmSize(e.target.value)} className={field}>
                <option value="">Select…</option>
                {FIRM_SIZES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <span className={label}>Practice areas</span>
              <CheckList options={PRACTICE_AREAS} selected={areas} onToggle={(v) => toggle(areas, setAreas, v)} />
            </div>
          </>
        )}

        {step === 1 && (
          <p className="text-sm text-neutral-400">
            As the principal, you&apos;ll be recorded as your firm&apos;s <strong className="text-neutral-200">compliance
            officer</strong> and <strong className="text-neutral-200">senior manager</strong> for AML/CTF purposes. You
            can delegate these later.
          </p>
        )}

        {step === 2 && (
          <>
            <p className="text-sm text-neutral-400">Which designated services does your firm provide?</p>
            <CheckList options={SERVICES} selected={services} onToggle={(v) => toggle(services, setServices, v)} />
          </>
        )}

        {step === 3 && (
          <>
            <p className="text-sm text-neutral-400">Which types of clients do you act for?</p>
            <CheckList options={CUSTOMER_TYPES} selected={customers} onToggle={(v) => toggle(customers, setCustomers, v)} />
          </>
        )}

        {step === 4 && (
          <>
            <p className="text-sm text-neutral-400">How do you typically onboard and deal with clients?</p>
            <CheckList options={CHANNELS} selected={channels} onToggle={(v) => toggle(channels, setChannels, v)} />
          </>
        )}

        {step === 5 && (
          <>
            <div>
              <label htmlFor="enrol" className={label}>AUSTRAC enrolment status</label>
              <select id="enrol" value={enrol} onChange={(e) => setEnrol(e.target.value)} className={field}>
                {ENROLMENT.map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            {enrol === "enrolled" && (
              <div>
                <label htmlFor="austrac" className={label}>Enrolment number</label>
                <input id="austrac" value={austrac} onChange={(e) => setAustrac(e.target.value)} className={field} />
              </div>
            )}
            {enrol !== "enrolled" && (
              <p className="text-xs text-neutral-500">
                We&apos;ll add an enrolment deadline (29 July 2026) to your compliance calendar.
              </p>
            )}
          </>
        )}

        {step === 6 && (
          <div className="space-y-2 text-sm text-neutral-400">
            <p>You&apos;re all set. When you finish, Onus will:</p>
            <ul className="list-inside list-disc space-y-1 text-neutral-300">
              <li>Calculate your firm&apos;s overall risk rating</li>
              <li>Generate your risk assessment for review</li>
              <li>Set up your compliance deadlines</li>
            </ul>
          </div>
        )}
      </div>

      {error && <p className="mt-4 text-sm text-red-400">{error}</p>}

      <div className="mt-8 flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          disabled={busy || step === 0}
          onClick={() => setStep((s) => Math.max(0, s - 1))}
        >
          Back
        </Button>
        <Button size="sm" onClick={next} disabled={busy}>
          {busy ? "Saving…" : step === STEP_TITLES.length - 1 ? "Finish onboarding" : "Continue"}
        </Button>
      </div>
    </div>
  );
}
