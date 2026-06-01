import { redirect } from "next/navigation";

import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();
  if (!session?.access_token) {
    redirect("/login");
  }

  // Gate the app behind onboarding: if the firm hasn't completed it, send them
  // to the wizard. Default to allowing through if the lookup fails.
  let onboardingCompleted = true;
  try {
    const res = await fetch(`${engineUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });
    if (res.ok) {
      const me = await res.json();
      onboardingCompleted = me?.firm?.onboarding_completed !== false;
    }
  } catch {
    onboardingCompleted = true;
  }

  if (!onboardingCompleted) {
    redirect("/onboarding");
  }

  return <DashboardShell>{children}</DashboardShell>;
}
