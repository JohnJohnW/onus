import Link from "next/link";

import { OnusMark } from "@/components/brand/onus-mark";

const FEATURES = [
  {
    title: "ML/TF risk assessment",
    body: "A documented risk profile across your services, clients, channels and countries, scored the way AUSTRAC expects (Step 2).",
  },
  {
    title: "AML/CTF program",
    body: "Sixteen policies mapped to the Act and Rules, drafted by AI and approved by a senior manager (s26P).",
  },
  {
    title: "Customer due diligence",
    body: "Tiered CDD with a before-you-act gate, beneficial-owner checks, and inline sanctions and PEP screening.",
  },
  {
    title: "Monitoring and SMRs",
    body: "Automated risk-condition scans and indicator alerts that escalate to a drafted suspicious matter report.",
  },
  {
    title: "Reporting and deadlines",
    body: "SMR, TTR and annual compliance reports with real deadlines, tipping-off guardrails and 7-year retention.",
  },
  {
    title: "Independent evaluation",
    body: "Scheduled, independence-gated evaluation of your program with findings and remediation (Step 5).",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
        <div className="flex items-center gap-2">
          <OnusMark className="h-7 w-7" />
          <span className="text-lg font-semibold tracking-tight">Onus</span>
        </div>
        <nav className="flex items-center gap-3 text-sm">
          <Link href="/login" className="text-neutral-300 transition hover:text-white">
            Sign in
          </Link>
          <Link
            href="/signup"
            className="rounded-md bg-neutral-100 px-3 py-1.5 font-medium text-neutral-900 transition hover:bg-white"
          >
            Get started
          </Link>
        </nav>
      </header>

      <section className="mx-auto max-w-3xl px-6 pb-16 pt-16 text-center sm:pt-24">
        <p className="mb-5 inline-block rounded-full border border-neutral-800 px-3 py-1 text-xs text-neutral-400">
          For Australian law firms - Tranche 2 reforms, from 1 July 2026
        </p>
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          An AI compliance officer for AML/CTF
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-neutral-400">
          Onus builds and maintains your AML/CTF program, runs customer due diligence
          before you act, monitors for suspicious activity, drafts the reports AUSTRAC
          requires, and keeps audit-ready records - with AI that drafts the paperwork
          and a human who approves it.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link
            href="/signup"
            className="rounded-md bg-neutral-100 px-5 py-2.5 text-sm font-medium text-neutral-900 transition hover:bg-white"
          >
            Get started
          </Link>
          <Link
            href="/login"
            className="rounded-md border border-neutral-800 px-5 py-2.5 text-sm font-medium text-neutral-200 transition hover:border-neutral-600"
          >
            Sign in
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-6 pb-20">
        <div className="grid gap-px overflow-hidden rounded-xl border border-neutral-800 bg-neutral-800 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="bg-neutral-950 p-6">
              <h3 className="text-sm font-medium text-neutral-100">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-neutral-400">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-6 pb-20">
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-6">
          <h2 className="text-sm font-medium text-neutral-200">
            Built for Australian data residency and the Privacy Act
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-neutral-400">
            Onus handles sensitive client and AML/CTF records. It is designed to run on
            Australian-hosted infrastructure so your data stays onshore, consistent with
            the Privacy Act 1988 (Australian Privacy Principles), AUSTRAC record-keeping,
            legal professional privilege, and your confidentiality obligations. Hosting
            outside Australia requires a documented cross-border (APP 8) assessment - see
            the deployment and data-residency guidance in the project README.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-neutral-500">
            Onus is software, not legal advice. Generated content is a starting point for
            a qualified person to review and approve.
          </p>
        </div>
      </section>

      <footer className="border-t border-neutral-900">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-2 px-6 py-6 text-xs text-neutral-500">
          <span>Onus - AML/CTF compliance for small Australian law firms</span>
          <Link href="/login" className="transition hover:text-neutral-300">
            Sign in
          </Link>
        </div>
      </footer>
    </main>
  );
}
