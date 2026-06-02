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

  // Gate the app: fail CLOSED on an auth failure. If the engine rejects the token
  // (e.g. the embedded access token has expired while the next-auth session rolled),
  // send the user to re-login rather than into empty "being prepared" pages. If the
  // firm hasn't finished onboarding, send them to the wizard. A transient network
  // error allows through, so a blip doesn't log everyone out. The redirects run
  // outside the try/catch - Next.js implements redirect() by throwing, and a catch
  // here would otherwise swallow it.
  let needsLogin = false;
  let onboardingCompleted = true;
  try {
    const res = await fetch(`${engineUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: "no-store",
    });
    if (res.status === 401 || res.status === 403) {
      needsLogin = true;
    } else if (res.ok) {
      const me = await res.json();
      onboardingCompleted = me?.firm?.onboarding_completed !== false;
    }
  } catch {
    onboardingCompleted = true;
  }

  if (needsLogin) {
    redirect("/login");
  }
  if (!onboardingCompleted) {
    redirect("/onboarding");
  }

  return <DashboardShell>{children}</DashboardShell>;
}
