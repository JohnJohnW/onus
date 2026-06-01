import { EvaluationView, type EvaluationsData } from "@/components/evaluation/evaluation-view";
import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

async function getEvaluations(token: string): Promise<EvaluationsData> {
  const fallback: EvaluationsData = {
    first_evaluation_deadline: null,
    enrolment_known: false,
    evaluations: [],
  };
  try {
    const res = await fetch(`${engineUrl}/evaluations`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as EvaluationsData) : fallback;
  } catch {
    return fallback;
  }
}

export default async function EvaluationPage() {
  const session = await auth();
  const token = session?.access_token;
  if (!token) return null;
  const data = await getEvaluations(token);
  return <EvaluationView data={data} />;
}
