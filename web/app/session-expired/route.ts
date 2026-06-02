import { signOut } from "@/lib/auth";

// Reached when the engine rejects our access token while the next-auth session
// cookie is still valid (the embedded engine token has a fixed 24h life, but the
// session cookie rolls forward on activity, so the two can disagree about whether
// the user is logged in). Middleware trusts the cookie and bounces authenticated
// users away from /login, so a plain redirect to /login from the dashboard layout
// loops forever. Clearing the session here makes both sides agree - logged out -
// so the user reaches /login and can re-authenticate for a fresh token.
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  // signOut() clears the session cookie and redirects by throwing, so the line
  // below is only a fallback if that behaviour ever changes.
  await signOut({ redirectTo: "/login?expired=1" });
  return Response.redirect(new URL("/login?expired=1", request.url), 303);
}
