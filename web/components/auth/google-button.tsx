"use client";

import { signIn } from "next-auth/react";
import { useEffect, useState } from "react";

// Shows a "Continue with Google" button only when the Google provider is configured
// (checked via next-auth's /api/auth/providers). Renders nothing otherwise, so the demo
// works with or without SSO set up.
export function GoogleButton({ callbackUrl = "/dashboard" }: { callbackUrl?: string }) {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    fetch("/api/auth/providers")
      .then((r) => (r.ok ? r.json() : null))
      .then((p) => setEnabled(!!(p && p.google)))
      .catch(() => setEnabled(false));
  }, []);

  if (!enabled) return null;

  return (
    <div className="mb-5">
      <button
        type="button"
        onClick={() => signIn("google", { callbackUrl })}
        className="flex w-full items-center justify-center gap-2 rounded-md border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm font-medium text-neutral-100 transition hover:border-neutral-500"
      >
        Continue with Google
      </button>
      <div className="my-4 flex items-center gap-3 text-xs text-neutral-600">
        <span className="h-px flex-1 bg-neutral-800" />
        or
        <span className="h-px flex-1 bg-neutral-800" />
      </div>
    </div>
  );
}
