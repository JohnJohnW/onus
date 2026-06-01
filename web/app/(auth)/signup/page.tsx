"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import { useState } from "react";

import { OnusMark } from "@/components/brand/onus-mark";

export default function SignupPage() {
  const router = useRouter();
  const [firmName, setFirmName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    const res = await fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        firm_name: firmName,
        full_name: fullName,
        email,
        password,
      }),
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(
        typeof data.detail === "string" ? data.detail : "Could not create your account.",
      );
      setLoading(false);
      return;
    }

    // Auto sign-in, then send the new firm to onboarding.
    const result = await signIn("credentials", { email, password, redirect: false });
    setLoading(false);
    if (!result || result.error) {
      router.push("/login");
      return;
    }
    router.push("/onboarding");
    router.refresh();
  }

  const field =
    "w-full rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm outline-none focus:border-neutral-600";
  const label = "mb-1 block text-sm text-neutral-400";

  return (
    <main className="flex min-h-screen items-center justify-center bg-neutral-950 px-4 py-12 text-neutral-100">
      <div className="w-full max-w-sm">
        <div className="mb-10 flex flex-col items-center gap-2">
          <OnusMark className="h-9 w-9" />
          <span className="text-2xl font-semibold tracking-tight">Onus</span>
        </div>
        <h1 className="mb-1 text-lg font-medium">Create your firm</h1>
        <p className="mb-6 text-sm text-neutral-400">Set up Onus for your practice.</p>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="firmName" className={label}>Firm name</label>
            <input id="firmName" required value={firmName} onChange={(e) => setFirmName(e.target.value)} className={field} />
          </div>
          <div>
            <label htmlFor="fullName" className={label}>Full name</label>
            <input id="fullName" required value={fullName} onChange={(e) => setFullName(e.target.value)} className={field} />
          </div>
          <div>
            <label htmlFor="email" className={label}>Email</label>
            <input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={field} />
          </div>
          <div>
            <label htmlFor="password" className={label}>Password</label>
            <input id="password" type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} className={field} />
            <p className="mt-1 text-xs text-neutral-500">At least 12 characters.</p>
          </div>
          <div>
            <label htmlFor="confirm" className={label}>Confirm password</label>
            <input id="confirm" type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} className={field} />
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-neutral-100 px-3 py-2 text-sm font-medium text-neutral-900 transition hover:bg-white disabled:opacity-50"
          >
            {loading ? "Creating account..." : "Create account"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-neutral-400">
          Already have an account?{" "}
          <Link href="/login" className="text-neutral-100 underline underline-offset-4">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
