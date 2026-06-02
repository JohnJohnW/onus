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
  if (!session) {
    // No session at all: middleware normally catches this first, but redirect
    // defensively. Unauthenticated, so /login won't bounce us back (no loop).
    redirect("/login");
  }
  if (!session.access_token) {
    // A session cookie exists but carries no engine token (stale/partial). Going
    // straight to /login would loop (middleware bounces authenticated cookies off
    // it), so clear the session first.
    redirect("/session-expired");
  }

  // Gate the app: fail CLOSED on an auth failure. If the engine rejects the token
  // (the embedded access token has a fixed 24h life while the next-auth session
  // cookie rolls forward, so the two can diverge), send the user to /session-expired,
  // which clears the stale cookie and forwards to /login for a fresh token. We must
  // NOT redirect straight to /login here: middleware bounces still-authenticated
  // cookies away from /login, which would loop forever. If the firm just hasn't
  // finished onboarding, send them to the wizard. A transient network error allows
  // through, so a blip doesn't log everyone out. The redirects run outside the
  // try/catch - Next.js implements redirect() by throwing, and a catch here would
  // otherwise swallow it.
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
    redirect("/session-expired");
  }
  if (!onboardingCompleted) {
    redirect("/onboarding");
  }

  return <DashboardShell>{children}</DashboardShell>;
}
