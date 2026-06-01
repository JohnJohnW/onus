import { RiskProfileView, type RiskAssessment } from "@/components/risk/risk-profile-view";
import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

async function getAssessment(token: string): Promise<RiskAssessment | null> {
  try {
    const res = await fetch(`${engineUrl}/risk-assessment/current`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as RiskAssessment) : null;
  } catch {
    return null;
  }
}

export default async function RiskProfilePage() {
  const session = await auth();
  const token = session?.access_token;
  const assessment = token ? await getAssessment(token) : null;

  if (!assessment) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Your Risk Profile</h1>
        <p className="mt-2 text-sm text-neutral-400">
          Your risk assessment is being prepared. Check back shortly.
        </p>
      </div>
    );
  }

  return <RiskProfileView assessment={assessment} />;
}
