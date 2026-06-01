import { redirect } from "next/navigation";

import { OnboardingWizard } from "@/components/onboarding/onboarding-wizard";
import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

export default async function OnboardingPage() {
  const session = await auth();
  if (!session?.access_token) {
    redirect("/login");
  }

  let completed = false;
  let initialStep = 0;
  try {
    const res = await fetch(`${engineUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });
    if (res.ok) {
      const me = await res.json();
      completed = me?.firm?.onboarding_completed === true;
      initialStep = me?.firm?.onboarding_step ?? 0;
    }
  } catch {
    // fall through and show the wizard from the start
  }

  if (completed) {
    redirect("/dashboard");
  }

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100">
      <OnboardingWizard initialStep={initialStep} />
    </main>
  );
}
