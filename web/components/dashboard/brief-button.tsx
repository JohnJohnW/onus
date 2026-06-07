"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/ui/markdown";
import { Spinner } from "@/components/ui/spinner";

export function BriefButton() {
  const [loading, setLoading] = useState(false);
  const [brief, setBrief] = useState<string | null>(null);
  const [err, setErr] = useState(false);

  async function run() {
    setLoading(true);
    setErr(false);
    const res = await fetch("/api/dashboard/brief", { method: "POST" });
    setLoading(false);
    if (res.ok) {
      const d = await res.json();
      setBrief(d.brief ?? null);
    } else {
      setErr(true);
    }
  }

  return (
    <div>
      <Button size="sm" variant="outline" onClick={run} disabled={loading}>
        {loading ? (
          <>
            <Spinner className="mr-2" />
            Briefing...
          </>
        ) : (
          "Brief me with Onus"
        )}
      </Button>
      {err && <p className="mt-2 text-xs text-red-400">Could not generate a brief right now.</p>}
      {brief && (
        <div className="mt-3 rounded-md border border-neutral-800 bg-neutral-900 p-3 text-sm">
          <Markdown content={brief} />
          <p className="mt-2 text-xs text-neutral-600">
            Drafted by Onus from your recent activity. Review before relying on it.
          </p>
        </div>
      )}
    </div>
  );
}
