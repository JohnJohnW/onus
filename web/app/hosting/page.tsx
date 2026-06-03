import Link from "next/link";

import { OnusMark } from "@/components/brand/onus-mark";
import { EoiForm } from "@/components/demo/eoi-form";

export const metadata = {
  title: "Onus - Demo hosting and data residency",
};

const TRADE_OFFS = [
  {
    title: "Where your data lives",
    demo: "Hosted in the United States (Vercel and US-region free tiers).",
    prod: "Hosted in an Australian region (e.g. Sydney, ap-southeast-2), so data stays onshore.",
  },
  {
    title: "Privacy Act / APP 8",
    demo: "US hosting is a cross-border disclosure - it would need a documented APP 8 assessment and provider agreements before real client data.",
    prod: "No cross-border disclosure to manage; the residency story is clean.",
  },
  {
    title: "Legal professional privilege",
    demo: "Documents and reports stored offshore carry subpoena / privilege-loss risk.",
    prod: "Onshore storage keeps privileged material under Australian jurisdiction.",
  },
  {
    title: "Backups and durability",
    demo: "Free tiers may sleep, and uploaded documents may not persist across restarts.",
    prod: "Managed Australian database with backups / point-in-time recovery; durable document storage.",
  },
  {
    title: "What is already production-grade",
    demo: "Tenant isolation (row-level security), server-only auth, the login throttle, the audit log and all the compliance logic are the same code in both.",
    prod: "Same - plus the hardening checklist (secrets manager, TLS, edge rate limiting, at-rest encryption) applied at the infrastructure layer.",
  },
];

export default function HostingPage() {
  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100">
      <header className="mx-auto flex max-w-3xl items-center justify-between px-6 py-5">
        <Link href="/" className="flex items-center gap-2">
          <OnusMark className="h-7 w-7" />
          <span className="text-lg font-semibold tracking-tight">Onus</span>
        </Link>
        <Link href="/login" className="text-sm text-neutral-300 transition hover:text-white">
          Sign in
        </Link>
      </header>

      <div className="mx-auto max-w-3xl px-6 pb-20 pt-6">
        <p className="mb-3 inline-block rounded-full border border-amber-900/60 bg-amber-950/30 px-3 py-1 text-xs text-amber-300">
          Demo stage
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Hosting and data residency</h1>
        <p className="mt-4 text-neutral-400">
          This is a demonstration of Onus. To make it free to try, the demo runs on US-based
          infrastructure (the front end on Vercel, with the engine and database on US free tiers).
          That is fine for evaluating the product, but it is <span className="text-neutral-200">not</span>{" "}
          suitable for real client AML/CTF data, which should stay in Australia. Do not enter genuine
          client information into the demo.
        </p>

        <h2 className="mt-10 text-sm font-medium uppercase tracking-wide text-neutral-500">
          Demo vs an Australian-hosted deployment
        </h2>
        <div className="mt-3 space-y-px overflow-hidden rounded-xl border border-neutral-800 bg-neutral-800">
          {TRADE_OFFS.map((t) => (
            <div key={t.title} className="bg-neutral-950 p-5">
              <p className="text-sm font-medium text-neutral-100">{t.title}</p>
              <div className="mt-2 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
                <p className="text-neutral-400">
                  <span className="text-amber-300">Demo: </span>
                  {t.demo}
                </p>
                <p className="text-neutral-400">
                  <span className="text-emerald-300">Australian-hosted: </span>
                  {t.prod}
                </p>
              </div>
            </div>
          ))}
        </div>

        <p className="mt-6 text-sm text-neutral-500">
          The full reasoning, the design trade-offs, and a step-by-step Australian deployment guide
          live in the project README and{" "}
          <code className="rounded bg-neutral-900 px-1 py-0.5 text-neutral-300">docs/deployment</code>.
        </p>

        <section className="mt-12 rounded-xl border border-neutral-800 bg-neutral-900/40 p-6">
          <h2 className="text-lg font-medium">Want it hosted properly in Australia?</h2>
          <p className="mt-2 text-sm text-neutral-400">
            Register your interest and we will follow up about an Australian-hosted deployment for
            your firm. No obligation.
          </p>
          <div className="mt-5">
            <EoiForm />
          </div>
        </section>

        <p className="mt-10 text-xs text-neutral-600">
          Onus is software, not legal advice. Generated content is a starting point for a qualified
          person to review and approve.
        </p>
      </div>
    </main>
  );
}
