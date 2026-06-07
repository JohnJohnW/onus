import { Card, CardContent } from "@/components/ui/card";
import { DownloadDocButtons } from "@/components/ui/download-doc";
import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

async function getJson<T>(path: string, token: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${engineUrl}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as T) : fallback;
  } catch {
    return fallback;
  }
}

type Program = { status: string };
type RiskAssessment = { status: string } | null;
type Report = { id: string; type: string; status: string };

function titleize(s: string): string {
  return s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export default async function DocumentsPage() {
  const session = await auth();
  const token = session?.access_token;
  if (!token) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
        <p className="mt-2 text-sm text-neutral-400">Could not load your documents right now.</p>
      </div>
    );
  }

  const [program, risk, reports] = await Promise.all([
    getJson<Program | null>("/program", token, null),
    getJson<RiskAssessment>("/risk-assessment/current", token, null),
    getJson<Report[]>("/reports", token, []),
  ]);
  const smrs = reports.filter((r) => r.type === "smr");

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
        <p className="mt-2 text-sm text-neutral-400">
          Onus prepares these for you. Download a current Word copy anytime to review, file, or
          hand to an external evaluator.
        </p>
      </header>

      <div className="space-y-3">
        <DocRow
          title="AML/CTF Compliance Program"
          status={program ? titleize(program.status) : "Not started"}
          href="/api/program/document"
        />
        <DocRow
          title="AML/CTF Risk Assessment"
          status={risk ? titleize(risk.status) : "Not started"}
          href={risk ? "/api/risk-assessment/document" : null}
        />
      </div>

      <section className="mt-10">
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Suspicious matter reports
        </h2>
        {smrs.length === 0 ? (
          <Card className="border-neutral-800 bg-neutral-900/50">
            <CardContent className="p-5 text-sm text-neutral-400">
              No suspicious matter reports yet.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {smrs.map((r) => (
              <DocRow
                key={r.id}
                title="Suspicious matter report (SMR)"
                status={titleize(r.status)}
                href={`/api/reports/${r.id}/document`}
              />
            ))}
          </div>
        )}
      </section>

      <section className="mt-10">
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Analyze a document
        </h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="p-5 text-sm text-neutral-400">
            To have Onus read a document and pull out the key details (beneficial owners, ID
            checks, source of funds, or a risk summary), open a client and use{" "}
            <span className="text-neutral-200">Analyze with Onus</span> in their{" "}
            <span className="text-neutral-200">Documents and evidence</span> section.{" "}
            <a href="/clients" className="text-neutral-300 underline hover:text-neutral-100">
              Go to clients
            </a>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function DocRow({ title, status, href }: { title: string; status: string; href: string | null }) {
  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="flex flex-wrap items-center justify-between gap-3 p-5">
        <div className="text-sm">
          <p className="text-neutral-200">{title}</p>
          <p className="mt-0.5 text-xs text-neutral-500">{status}</p>
        </div>
        {href ? (
          <DownloadDocButtons path={href} />
        ) : (
          <span className="text-xs text-neutral-600">Not available yet</span>
        )}
      </CardContent>
    </Card>
  );
}
