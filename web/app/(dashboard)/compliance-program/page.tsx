import { ProgramView, type Program } from "@/components/program/program-view";
import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

async function getProgram(token: string): Promise<Program | null> {
  try {
    const res = await fetch(`${engineUrl}/program`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as Program) : null;
  } catch {
    return null;
  }
}

export default async function ComplianceProgramPage() {
  const session = await auth();
  const program = session?.access_token ? await getProgram(session.access_token) : null;

  if (!program) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Compliance Program</h1>
        <p className="mt-2 text-sm text-neutral-400">
          Your AML/CTF program is being prepared. Check back shortly.
        </p>
      </div>
    );
  }

  return <ProgramView program={program} />;
}
