"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function CompleteDeadlineButton({ id }: { id: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function complete() {
    setBusy(true);
    const res = await fetch(`/api/dashboard/deadlines/${id}/complete`, { method: "POST" });
    setBusy(false);
    if (res.ok) router.refresh();
  }

  return (
    <button
      type="button"
      onClick={complete}
      disabled={busy}
      className="shrink-0 whitespace-nowrap text-xs text-neutral-500 hover:text-neutral-200"
    >
      {busy ? "..." : "Mark done"}
    </button>
  );
}
