import { Card, CardContent } from "@/components/ui/card";

// Grounded in AUSTRAC's official guidance (austrac.gov.au), verified 2026: tranche-2
// enrolment opens 31 Mar 2026, the deadline is 29 Jul 2026, obligations start 1 Jul 2026.
// Law firms ENROL only (no registration; that is for remittance / virtual-asset providers),
// AUSTRAC Online uses email + password + an authenticator app (no myGovID or RAM), and there
// is no enrolment fee (the industry levy applies only to large entities).
const AUSTRAC_ENROL_URL = "https://www.austrac.gov.au/new-austrac/enrol-or-register/enrol-us";

function titleize(s: string): string {
  return s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function EnrolmentGuide({
  enrolmentStatus,
  austracNumber,
}: {
  enrolmentStatus: string;
  austracNumber: string | null;
}) {
  const enrolled = enrolmentStatus === "enrolled";
  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="space-y-4 p-5 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-neutral-400">AUSTRAC enrolment status</span>
          <span className={enrolled ? "font-medium text-emerald-300" : "font-medium text-amber-300"}>
            {titleize(enrolmentStatus)}
            {austracNumber ? ` - ${austracNumber}` : ""}
          </span>
        </div>

        {enrolled ? (
          <div className="space-y-2 text-neutral-300">
            <p>Your firm is enrolled on the AUSTRAC Reporting Entities Roll.</p>
            <p className="text-neutral-400">
              Keep your details current: notify AUSTRAC within 14 days if your business or the
              designated services you provide change.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-amber-200">
              <p className="font-medium">Key dates</p>
              <ul className="mt-1 space-y-0.5 text-amber-100/90">
                <li>Enrolment opens: 31 March 2026</li>
                <li>Enrol by: 29 July 2026</li>
                <li>Obligations start: 1 July 2026</li>
              </ul>
            </div>

            <div>
              <p className="mb-1 font-medium text-neutral-200">How to enrol</p>
              <ol className="list-inside list-decimal space-y-1 text-neutral-300">
                <li>
                  Confirm your firm provides a designated service (conveyancing, holding or managing
                  client money, setting up companies or trusts, and similar).
                </li>
                <li>
                  Create an AUSTRAC Online account: an email, a password, and an authenticator app
                  for multi-factor sign-in. You do not need myGovID or RAM.
                </li>
                <li>Complete and submit the enrolment form (what you will need is below).</li>
                <li>
                  You receive a submission receipt and an AUSTRAC Account Number (AAN), then an email
                  confirming you are enrolled.
                </li>
              </ol>
            </div>

            <div>
              <p className="mb-1 font-medium text-neutral-200">What you will need</p>
              <ul className="list-inside list-disc space-y-0.5 text-neutral-300">
                <li>Legal name and ABN (and ACN if a company)</li>
                <li>Business address and contact details</li>
                <li>The designated services your firm provides</li>
                <li>Your AML/CTF compliance officer&apos;s details (or a primary contact for AUSTRAC)</li>
              </ul>
            </div>

            <p className="text-neutral-400">
              Enrol only - law firms do not register (that is for remittance and virtual-asset
              providers). There is no fee to enrol; the only AUSTRAC charge is the annual industry
              contribution levy, which applies to large entities, so a small firm pays nil.
            </p>

            <a
              href={AUSTRAC_ENROL_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block rounded-md border border-neutral-700 px-3 py-1.5 text-xs text-neutral-100 hover:bg-neutral-800"
            >
              Open AUSTRAC enrolment
            </a>
          </div>
        )}

        <p className="text-xs text-neutral-600">
          Onus guides you; you complete enrolment on AUSTRAC&apos;s own secure portal. General
          guidance, not legal advice - confirm details at austrac.gov.au.
        </p>
      </CardContent>
    </Card>
  );
}
