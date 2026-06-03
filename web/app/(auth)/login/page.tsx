"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import { useEffect, useState } from "react";

import { GoogleButton } from "@/components/auth/google-button";
import { OnusMark } from "@/components/brand/onus-mark";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [expired, setExpired] = useState(false);

  // Read the flag from window (not useSearchParams) to keep this page out of a
  // Suspense boundary. Set by /session-expired after a stale session is cleared.
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("expired")) {
      setExpired(true);
    }
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const result = await signIn("credentials", { email, password, redirect: false });
    setLoading(false);
    if (!result || result.error) {
      setError("Invalid email or password.");
      return;
    }
    router.push("/dashboard");
    router.refresh();
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-neutral-950 px-4 text-neutral-100">
      <div className="w-full max-w-sm">
        <div className="mb-10 flex flex-col items-center gap-2">
          <OnusMark className="h-9 w-9" />
          <span className="text-2xl font-semibold tracking-tight">Onus</span>
        </div>
        <h1 className="mb-1 text-lg font-medium">Sign in</h1>
        <p className="mb-6 text-sm text-neutral-400">Welcome back.</p>
        {expired && (
          <p className="mb-4 rounded-md border border-amber-900/50 bg-amber-950/40 px-3 py-2 text-sm text-amber-300">
            Your session expired. Please sign in again to continue.
          </p>
        )}
        <GoogleButton callbackUrl="/dashboard" />
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1 block text-sm text-neutral-400">Email</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-600"
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-sm text-neutral-400">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-600"
            />
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-900 transition hover:bg-white disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-neutral-400">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="text-neutral-100 underline underline-offset-4">
            Create one
          </Link>
        </p>
      </div>
    </main>
  );
}
