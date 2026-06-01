import type { DefaultSession } from "next-auth";

declare module "next-auth" {
  /** Fields returned from the Credentials `authorize` callback. */
  interface User {
    firm_id?: string;
    role?: string;
    access_token?: string;
  }

  /** Session shape exposed to the app (see the `session` callback in lib/auth). */
  interface Session {
    user_id: string;
    firm_id: string;
    role: string;
    access_token: string;
    user: {
      id?: string;
    } & DefaultSession["user"];
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    user_id?: string;
    firm_id?: string;
    role?: string;
    access_token?: string;
  }
}
