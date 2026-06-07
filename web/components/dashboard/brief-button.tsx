"use client";

import { useState } from "react";

import type { AiAction } from "@/components/ai/action-link";
import { AiDisclaimer, AiResultCard, FindingCard, SectionLabel } from "@/components/ai/result-card";
import { SEVERITY_ORDER, severityOf } from "@/components/ai/severity";
import { Button } from "@/components/ui/button";
import { Markdown } from "@/components/ui/markdown";
import { Spinner } from "@/components/ui/spinner";

type BriefItem = { severity: string; title: string; detail: string; action_key?: string };
type Brief = { headline?: string | null; items?: BriefItem[]; brief?: string | null };

const BRIEF_ACTIONS: Record<string, AiAction> = {
  open_risk_profile: { mode: "navigate", label: "Open risk profile", href: "/risk-profile" },
  review_clients: { mode: "navigate", label: "Review clients", href: "/clients" },
  open_program: { mode: "navigate", label: "Open program", href: "/compliance-program" },
  open_reporting: { mode: "navigate", label: "Open reporting", href: "/reporting" },
  open_documents: { mode: "navigate", label: "Open documents", href: "/documents" },
};

export function BriefButton() {
  const [loading, setLoading] = useState(false);
  const [brief, setBrief] = useState<Brief | null>(null);
  const [err, setErr] = useState(false);

  async function run() {
    setLoading(true);
    setErr(false);
    const res = await fetch("/api/dashboard/brief", { method: "POST" });
    setLoading(false);
    if (res.ok) {
      setBrief(await res.json());
    } else {
      setErr(true);
    }
  }

  const items = brief?.items
    ? [...brief.items].sort(
        (a, b) => SEVERITY_ORDER[severityOf(a.severity)] - SEVERITY_ORDER[severityOf(b.severity)]
      )
    : [];

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
        <AiResultCard title="Brief from Onus">
          {brief.headline && (
            <p className="text-base font-medium leading-snug text-neutral-100">{brief.headline}</p>
          )}
          {items.length > 0 && (
            <div className="space-y-2">
              <SectionLabel>What needs you</SectionLabel>
              {items.map((it, i) => (
                <FindingCard
                  key={i}
                  severity={it.severity}
                  title={it.title}
                  detail={it.detail}
                  action={
                    it.action_key && it.action_key !== "none" ? BRIEF_ACTIONS[it.action_key] : undefined
                  }
                />
              ))}
            </div>
          )}
          {!brief.headline && items.length === 0 && brief.brief && <Markdown content={brief.brief} />}
          <AiDisclaimer>Drafted by Onus from your recent activity. Review before relying on it.</AiDisclaimer>
        </AiResultCard>
      )}
    </div>
  );
}
