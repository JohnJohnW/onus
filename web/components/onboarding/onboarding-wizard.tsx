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
                active ? "border-neutral-100 bg-neutral-100 text-neutral-900" : "border-neutral-600"
              )}
            >
              {active && (
                <svg
                  viewBox="0 0 16 16"
                  className="h-3 w-3"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2.5}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M3.5 8.5l3 3 6-7" />
                </svg>
              )}
            </span>
            {opt}
          </button>
        );
      })}
    </div>
  );
}

export function OnboardingWizard({
  initialStep = 0,
  initialFirmName = "",
}: {
  initialStep?: number;
  initialFirmName?: string;
}) {
  const router = useRouter();
  const [step, setStep] = useState(Math.min(Math.max(initialStep, 0), STEP_TITLES.length - 1));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const [firmName, setFirmName] = useState(initialFirmName);
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
    if (step === 0) {
      if (!firmName.trim()) {
        setError("Enter your firm name.");
        return;
      }
      ok = await post("firm_details", {
        firm_name: firmName.trim(),
        abn,
        firm_size: firmSize,
        practice_areas: areas,
      });
    }
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
              <label htmlFor="firmName" className={label}>Firm name</label>
              <input
                id="firmName"
                value={firmName}
                onChange={(e) => setFirmName(e.target.value)}
                className={field}
                placeholder="Your firm's name"
              />
            </div>
            <div>
              <label htmlFor="abn" className={label}>ABN</label>
              <input id="abn" value={abn} onChange={(e) => setAbn(e.target.value)} className={field} placeholder="11 digits" />
            </div>
            <div>
              <label htmlFor="firmSize" className={label}>Firm size</label>
              <select id="firmSize" value={firmSize} onChange={(e) => setFirmSize(e.target.value)} className={field}>
                <option value="">Select...</option>
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

        {step === 1 &&
          (firmSize === "Sole practitioner" ? (
            <p className="text-sm leading-relaxed text-neutral-400">
              As a sole practitioner you&apos;ll act as your firm&apos;s{" "}
              <strong className="text-neutral-200">compliance officer</strong>,{" "}
              <strong className="text-neutral-200">senior manager</strong> and{" "}
              <strong className="text-neutral-200">governing body</strong> for AML/CTF purposes -
              one person holding all three roles is expressly allowed (s26J, ss26N-26P). You can
              add colleagues and reassign roles anytime in Settings.
            </p>
          ) : (
            <p className="text-sm leading-relaxed text-neutral-400">
              You&apos;ll be set as your firm&apos;s{" "}
              <strong className="text-neutral-200">compliance officer</strong> (day-to-day
              AML/CTF; must be management level, an Australian resident, and fit and proper -
              s26J) and the <strong className="text-neutral-200">senior manager</strong> who
              approves the program (ss26N-26P); your{" "}
              <strong className="text-neutral-200">governing body</strong> oversees it. Good
              practice is to separate the compliance officer from the approving senior manager
              where you can - once you&apos;ve added colleagues you can assign different people in
              Settings. Senior-manager approval can&apos;t be delegated.
            </p>
          ))}

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
          {busy ? "Saving..." : step === STEP_TITLES.length - 1 ? "Finish onboarding" : "Continue"}
        </Button>
      </div>
    </div>
  );
}
