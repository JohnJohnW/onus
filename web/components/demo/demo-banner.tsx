"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

// Shows only when NEXT_PUBLIC_DEMO=true (set on the public demo deployment). On local
// dev and a real Australian-hosted deployment the flag is unset, so this renders nothing.
export function DemoBanner() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (process.env.NEXT_PUBLIC_DEMO !== "true") return;
    if (window.localStorage.getItem("onus-demo-dismissed") === "1") return;
    setShow(true);
  }, []);

  if (!show) return null;

  return (
    <div className="sticky top-0 z-50 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 border-b border-amber-900/50 bg-amber-950/90 px-4 py-2 text-center text-xs text-amber-200 backdrop-blur">
      <span>
        <span className="font-semibold">Demo:</span> your data is hosted in the US (via Vercel),
        not Australia. Please do not enter real client data.
      </span>
      <Link href="/hosting" className="underline underline-offset-2 hover:text-white">
        See the trade-offs and request Australian hosting
      </Link>
      <button
        type="button"
        onClick={() => {
          window.localStorage.setItem("onus-demo-dismissed", "1");
          setShow(false);
        }}
        aria-label="Dismiss demo notice"
        className="ml-1 rounded px-1 text-amber-300/80 hover:text-white"
      >
        Dismiss
      </button>
    </div>
  );
}
