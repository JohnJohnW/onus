"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";

export function RunMonitoringButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setMsg(null);
    const res = await fetch("/api/alerts/scan", { method: "POST" });
    setBusy(false);
    if (res.ok) {
      const d = await res.json();
      setMsg(
        d.raised === 0
          ? "No new risk conditions found."
          : `Raised ${d.raised} alert${d.raised === 1 ? "" : "s"}.`
      );
      router.refresh();
    } else {
      setMsg("Could not run the scan.");
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button size="sm" variant="outline" disabled={busy} onClick={run}>
        {busy ? "Scanning..." : "Run monitoring scan"}
      </Button>
      {msg && <span className="text-xs text-neutral-400">{msg}</span>}
    </div>
  );
}
