import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import Google from "next-auth/providers/google";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

// SSO is enabled only when Google OAuth credentials are configured.
const googleEnabled =
  !!process.env.GOOGLE_CLIENT_ID && !!process.env.GOOGLE_CLIENT_SECRET;

// Exchange a verified OAuth identity for an engine token via the secret-gated bridge
// (/auth/oauth). The shared OAUTH_BRIDGE_SECRET proves the call comes from this web tier.
// Returns the engine AuthResponse, or null on failure (the user then lands back at login).
async function exchangeOAuth(
  email: string,
  fullName: string | null,
): Promise<{ access_token: string; user: { id: string; firm_id: string; role: string } } | null> {
  try {
    const res = await fetch(`${engineUrl}/auth/oauth`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Internal-Secret": process.env.OAUTH_BRIDGE_SECRET ?? "",
      },
      body: JSON.stringify({ email, full_name: fullName, provider: "google" }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

// The engine token lives 24h. Renew it once it is past the halfway point of that
// life, so any active session (every request through the layout or a proxy runs the
// jwt callback) is refreshed well before expiry and never logged out mid-use. A
// token with less than this much life left and an idle user simply lapses, and the
// /session-expired route routes them to a clean re-login.
const REFRESH_WHEN_REMAINING_MS = 12 * 60 * 60 * 1000;

// Read a JWT's `exp` claim (seconds) as epoch milliseconds, without verifying the
// signature - the engine still validates every token; the web tier only needs to
// know when to refresh. Uses atob (not Node's Buffer) so it is safe in the Edge
// runtime, where the jwt callback also runs during middleware.
function accessTokenExpiry(token: string): number {
  try {
    const payload = token.split(".")[1];
    const b64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const claims = JSON.parse(atob(padded));
    return typeof claims.exp === "number" ? claims.exp * 1000 : 0;
  } catch {
    return 0;
  }
}

// Trade a still-valid engine token for a fresh one. Returns null on any failure, so
// the caller keeps the current token and lets it lapse normally if it cannot renew.
async function refreshAccessToken(currentToken: string): Promise<string | null> {
  try {
    const res = await fetch(`${engineUrl}/auth/refresh`, {
      method: "POST",
      headers: { Authorization: `Bearer ${currentToken}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return typeof data?.access_token === "string" ? data.access_token : null;
  } catch {
    return null;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  secret: process.env.NEXTAUTH_SECRET,
  session: { strategy: "jwt", maxAge: 24 * 60 * 60 }, // 24 hours
  pages: { signIn: "/login" },
  providers: [
    Credentials({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      authorize: async (credentials) => {
        if (!credentials?.email || !credentials?.password) return null;
        const res = await fetch(`${engineUrl}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: credentials.email,
            password: credentials.password,
          }),
        });
        if (!res.ok) return null;
        const data = await res.json();
        const u = data.user;
        return {
          id: u.id,
          email: u.email,
          name: u.full_name,
          firm_id: u.firm_id,
          role: u.role,
          access_token: data.access_token,
        };
      },
    }),
    ...(googleEnabled
      ? [
          Google({
            clientId: process.env.GOOGLE_CLIENT_ID,
            clientSecret: process.env.GOOGLE_CLIENT_SECRET,
          }),
        ]
      : []),
  ],
  callbacks: {
    async jwt({ token, user, account, profile }) {
      // SSO sign-in: exchange the provider-verified email for an engine token.
      if (account?.provider === "google") {
        const email = typeof profile?.email === "string" ? profile.email : null;
        const name = typeof profile?.name === "string" ? profile.name : null;
        if (email) {
          const data = await exchangeOAuth(email, name);
          if (data?.access_token) {
            token.user_id = data.user.id;
            token.firm_id = data.user.firm_id;
            token.role = data.user.role;
            token.access_token = data.access_token;
            token.access_token_expires = accessTokenExpiry(data.access_token);
          }
        }
        return token;
      }
      if (user) {
        // Sign-in: capture the freshly minted engine token and its expiry.
        token.user_id = user.id as string;
        token.firm_id = user.firm_id;
        token.role = user.role;
        token.access_token = user.access_token;
        token.access_token_expires = user.access_token
          ? accessTokenExpiry(user.access_token)
          : 0;
        return token;
      }

      // Existing session: silently renew the engine token once it is past the
      // halfway point of its life, so an active session is never logged out
      // mid-use. On any failure keep the current token (it lapses normally).
      // typeof-narrow rather than trust the JWT field types (v5 reads them loosely).
      const current =
        typeof token.access_token === "string" ? token.access_token : null;
      const expires =
        typeof token.access_token_expires === "number"
          ? token.access_token_expires
          : 0;
      const remaining = expires - Date.now();
      if (current && remaining > 0 && remaining < REFRESH_WHEN_REMAINING_MS) {
        const refreshed = await refreshAccessToken(current);
        if (refreshed) {
          token.access_token = refreshed;
          token.access_token_expires = accessTokenExpiry(refreshed);
        }
      }
      return token;
    },
    async session({ session, token }) {
      session.user_id = token.user_id as string;
      session.firm_id = token.firm_id as string;
      session.role = token.role as string;
      session.access_token = token.access_token as string;
      if (session.user) {
        session.user.id = token.user_id as string;
      }
      return session;
    },
  },
});

/**
 * Server-side session accessor. next-auth v5 exposes this as `auth()`; this
 * wrapper keeps the conventional `getServerSession` name for callers.
 */
export async function getServerSession() {
  return auth();
}
