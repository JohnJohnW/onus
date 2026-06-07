import { CheckCircle2, Circle } from "lucide-react";
import Link from "next/link";

import { ProgressRing } from "@/components/charts/progress-ring";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { BriefButton } from "@/components/dashboard/brief-button";
import { CompleteDeadlineButton } from "@/components/dashboard/complete-deadline-button";
import { Greeting } from "@/components/dashboard/greeting";
import { RiskBadge } from "@/components/dashboard/risk-badge";
import { RunMonitoringButton } from "@/components/dashboard/run-monitoring-button";
import { auth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { daysRemainingLabel, daysRemainingTone, formatDate, relativeTime } from "@/lib/format";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

type PendingAction = {
  id: string;
  kind: string;
  title: string;
  why: string;
  estimate_label: string | null;
  action_label: string;
  href: string | null;
  due_at: string | null;
  days_remaining: number | null;
};
type AgentActivity = {
  id: string;
  summary: string;
  created_at: string;
  human_action_required: boolean;
  human_action_label: string | null;
  href: string | null;
};
type UpcomingDeadline = { id: string; name: string; due_at: string; days_remaining: number };
type ReadinessMilestone = { key: string; label: string; done: boolean; href: string };
type Summary = {
  firm_risk_rating: string;
  readiness?: { percent: number; milestones: ReadinessMilestone[] };
  pending_actions: PendingAction[];
  recent_agent_activity: AgentActivity[];
  upcoming_deadlines: UpcomingDeadline[];
};

async function getSummary(token: string): Promise<Summary | null> {
  try {
    const res = await fetch(`${engineUrl}/dashboard/summary`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as Summary) : null;
  } catch {
    return null;
  }
}

async function getFirmName(token: string): Promise<string | null> {
  try {
    const res = await fetch(`${engineUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!res.ok) return null;
    const me = await res.json();
    return me?.firm?.name ?? null;
  } catch {
    return null;
  }
}


export default async function DashboardPage() {
  const session = await auth();
  const token = session?.access_token;
  const firstName = (session?.user?.name ?? "").trim().split(" ")[0] || "there";

  const [summary, firmName] = await Promise.all([
    token ? getSummary(token) : Promise.resolve(null),
    token ? getFirmName(token) : Promise.resolve(null),
  ]);

  const rating = summary?.firm_risk_rating ?? "unassessed";
  const actions = summary?.pending_actions ?? [];
  const activity = summary?.recent_agent_activity ?? [];
  const deadlines = summary?.upcoming_deadlines ?? [];
  const overdue = deadlines.filter((d) => d.days_remaining !== null && d.days_remaining < 0);
  const dueSoon = deadlines.filter(
    (d) => d.days_remaining !== null && d.days_remaining >= 0 && d.days_remaining < 14
  );

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <header className="mb-10">
        <Greeting firstName={firstName} />
        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-neutral-400">
          <span>{firmName ?? "Your firm"}</span>
          <span aria-hidden>-</span>
          <RiskBadge rating={rating} />
          <span>risk profile</span>
        </div>
      </header>

      <div className="mb-8 flex flex-wrap gap-2">
        <Button asChild size="sm" variant="outline">
          <Link href="/clients">New client</Link>
        </Button>
        <Button asChild size="sm" variant="outline">
          <Link href="/settings">Screen a name</Link>
        </Button>
        <Button asChild size="sm" variant="outline">
          <Link href="/reporting">Draft a report</Link>
        </Button>
        <Button asChild size="sm" variant="outline">
          <Link href="/documents">Documents</Link>
        </Button>
      </div>

      {summary?.readiness && (
        <div className="mb-8 rounded-lg border border-neutral-800 bg-neutral-900/40 p-5">
          <div className="flex items-center gap-5">
            <ProgressRing percent={summary.readiness.percent} label="ready" />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-neutral-200">Compliance readiness</p>
              <p className="text-xs text-neutral-500">Your path to AML/CTF obligations from 1 July 2026.</p>
              <div className="mt-3 grid gap-1 sm:grid-cols-2">
                {summary.readiness.milestones.map((m) => (
                  <Link
                    key={m.key}
                    href={m.href}
                    className="flex items-center gap-2 rounded px-1.5 py-1 text-sm hover:bg-neutral-800/50"
                  >
                    {m.done ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                    ) : (
                      <Circle className="h-4 w-4 shrink-0 text-neutral-600" />
                    )}
                    <span className={m.done ? "text-neutral-400" : "text-neutral-200"}>{m.label}</span>
                  </Link>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {(overdue.length > 0 || dueSoon.length > 0) && (
        <div
          className={cn(
            "mb-8 rounded-lg border p-4 text-sm",
            overdue.length > 0
              ? "border-red-500/30 bg-red-500/10 text-red-200"
              : "border-amber-500/30 bg-amber-500/10 text-amber-200"
          )}
        >
          <span className="font-medium">Reminders: </span>
          {overdue.length > 0 && (
            <>
              {overdue.length} deadline{overdue.length === 1 ? "" : "s"} overdue
              {dueSoon.length > 0 ? ", " : ". "}
            </>
          )}
          {dueSoon.length > 0 && (
            <>
              {dueSoon.length} due within 14 days.{" "}
            </>
          )}
          <a href="#deadlines" className="font-medium underline underline-offset-2">
            See upcoming deadlines below.
          </a>
        </div>
      )}

      <div className="mb-8 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
        <span className="text-sm text-neutral-400">
          Onus monitors your firm for sanctions, PEP and CDD risk conditions.
        </span>
        <RunMonitoringButton />
      </div>

      <div className="mb-8 rounded-lg border border-neutral-800 bg-neutral-900/40 p-4">
        <p className="mb-3 text-sm text-neutral-400">
          Get a plain-English brief of what Onus has done and what needs your attention.
        </p>
        <BriefButton />
      </div>

      {/* Section 1 - Action required */}
      <Section title="Action required">
        {actions.length === 0 ? (
          <EmptyState>No action required right now. Onus is monitoring your firm.</EmptyState>
        ) : (
          <div className="space-y-3">
            {actions.map((a) => (
              <Card key={a.id} className="border-neutral-800 bg-neutral-900/50">
                <CardContent className="flex items-start justify-between gap-4 p-5">
                  <div className="min-w-0">
                    <p className="font-medium text-neutral-100">{a.title}</p>
                    <p className="mt-1 text-sm text-neutral-400">{a.why}</p>
                    <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-neutral-500">
                      {a.estimate_label && <span>{a.estimate_label}</span>}
                      {a.estimate_label && a.days_remaining !== null && (
                        <span aria-hidden>-</span>
                      )}
                      {a.days_remaining !== null && (
                        <span className={daysRemainingTone(a.days_remaining)}>
                          {daysRemainingLabel(a.days_remaining)}
                        </span>
                      )}
                    </div>
                  </div>
                  {a.href && (
                    <Button asChild size="sm" className="shrink-0">
                      <Link href={a.href}>{a.action_label}</Link>
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </Section>

      {/* Section 2 - Onus activity */}
      <Section title="Onus activity">
        {activity.length === 0 ? (
          <EmptyState>
            Onus will start monitoring your firm shortly. Activity will appear here.
          </EmptyState>
        ) : (
          <div className="space-y-3">
            {activity.map((t) => (
              <Card key={t.id} className="border-neutral-800 bg-neutral-900/50">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-4">
                    <p className="text-sm text-neutral-200">{t.summary}</p>
                    <span className="shrink-0 whitespace-nowrap text-xs text-neutral-500">
                      {relativeTime(t.created_at)}
                    </span>
                  </div>
                  {t.human_action_required && (
                    <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs text-amber-400">
                        {t.human_action_label ?? "Needs your attention"}
                      </p>
                      {t.href && (
                        <Button asChild size="sm" variant="outline" className="shrink-0">
                          <Link href={t.href}>Review now</Link>
                        </Button>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </Section>

      {/* Section 3 - Upcoming deadlines */}
      <Section title="Upcoming deadlines" id="deadlines">
        {deadlines.length === 0 ? (
          <EmptyState>No upcoming deadlines.</EmptyState>
        ) : (
          <Card className="border-neutral-800 bg-neutral-900/50">
            <CardContent className="divide-y divide-neutral-800 p-0">
              {deadlines.map((d) => (
                <div key={d.id} className="flex items-center justify-between gap-4 px-5 py-4">
                  <div className="min-w-0">
                    <p className="truncate text-sm text-neutral-200">{d.name}</p>
                    <p className="mt-0.5 text-xs text-neutral-500">{formatDate(d.due_at)}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-4">
                    <span
                      className={cn(
                        "whitespace-nowrap text-xs font-medium",
                        daysRemainingTone(d.days_remaining)
                      )}
                    >
                      {daysRemainingLabel(d.days_remaining)}
                    </span>
                    <CompleteDeadlineButton id={d.id} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </Section>
    </div>
  );
}

function Section({ title, id, children }: { title: string; id?: string; children: React.ReactNode }) {
  return (
    <section id={id} className="mb-10">
      <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">{title}</h2>
      {children}
    </section>
  );
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return (
    <Card className="border-neutral-800 bg-neutral-900/30">
      <CardContent className="p-6 text-sm text-neutral-400">{children}</CardContent>
    </Card>
  );
}
