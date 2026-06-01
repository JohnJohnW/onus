import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

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
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.user_id = user.id as string;
        token.firm_id = user.firm_id;
        token.role = user.role;
        token.access_token = user.access_token;
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
