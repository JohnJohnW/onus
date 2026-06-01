import Link from "next/link";

import { auth } from "@/lib/auth";

export default async function OnboardingPage() {
  const session = await auth();
  const firstName = (session?.user?.name ?? "").trim().split(" ")[0] || "there";

  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center bg-neutral-950 px-6 text-center text-neutral-100">
      <span className="mb-8 text-2xl font-semibold tracking-tight">Onus</span>
      <h1 className="text-xl font-medium">Welcome, {firstName}.</h1>
      <p className="mt-2 max-w-sm text-sm text-neutral-400">
        Your firm is set up. This is where Onus will walk you through standing up your AML/CTF
        program.
      </p>
      <Link
        href="/dashboard"
        className="mt-8 rounded-md bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 transition hover:bg-white"
      >
        Continue to dashboard
      </Link>
    </div>
  );
}
