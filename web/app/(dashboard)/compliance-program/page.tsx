import {
  ProgramView,
  type Lifecycle,
  type Program,
} from "@/components/program/program-view";
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

export default async function ComplianceProgramPage() {
  const session = await auth();
  const token = session?.access_token;
  const program = token ? await getJson<Program | null>("/program", token, null) : null;

  if (!program) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Compliance Program</h1>
        <p className="mt-2 text-sm text-neutral-400">
          We could not load your compliance program right now. Refresh the page to try again, or{" "}
          <a href="/onboarding" className="text-neutral-200 underline">complete onboarding</a>{" "}
          if you have not set up your firm yet.
        </p>
      </div>
    );
  }

  const lifecycle = token
    ? await getJson<Lifecycle | null>("/program/lifecycle", token, null)
    : null;

  return <ProgramView program={program} lifecycle={lifecycle} />;
}
