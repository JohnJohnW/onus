import { Card, CardContent } from "@/components/ui/card";
import { auth } from "@/lib/auth";
import { relativeTime } from "@/lib/format";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

type Entry = {
  id: string;
  action: string;
  entity_type: string | null;
  actor: string | null;
  created_at: string;
};

const ACTION_LABELS: Record<string, string> = {
  "onboarding.completed": "Completed onboarding",
  "risk_assessment.approved": "Approved the risk assessment",
  "risk_assessment.changes_requested": "Requested changes to the risk assessment",
};

function label(action: string): string {
  return ACTION_LABELS[action] ?? action.replace(/[._]/g, " ");
}

async function getLog(token: string): Promise<Entry[]> {
  try {
    const res = await fetch(`${engineUrl}/audit-log`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as Entry[]) : [];
  } catch {
    return [];
  }
}

export default async function AuditTrailPage() {
  const session = await auth();
  const entries = session?.access_token ? await getLog(session.access_token) : [];

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Audit Trail</h1>
          <p className="mt-2 text-sm text-neutral-400">
            A complete, timestamped record of every action taken in your account.
          </p>
        </div>
        {entries.length > 0 && (
          <a
            href="/api/audit-log/export"
            className="shrink-0 rounded-md border border-neutral-800 px-3 py-1.5 text-sm text-neutral-200 transition hover:border-neutral-600"
          >
            Export CSV
          </a>
        )}
      </div>

      <div className="mt-8">
        {entries.length === 0 ? (
          <Card className="border-neutral-800 bg-neutral-900/30">
            <CardContent className="p-6 text-sm text-neutral-400">
              No activity recorded yet.
            </CardContent>
          </Card>
        ) : (
          <Card className="border-neutral-800 bg-neutral-900/50">
            <CardContent className="divide-y divide-neutral-800 p-0">
              {entries.map((e) => (
                <div key={e.id} className="flex items-start justify-between gap-4 px-5 py-4">
                  <div className="min-w-0">
                    <p className="text-sm capitalize text-neutral-200">{label(e.action)}</p>
                    <p className="mt-0.5 text-xs text-neutral-500">
                      {e.actor ?? "Onus"}
                      {e.entity_type ? ` - ${e.entity_type.replace(/_/g, " ")}` : ""}
                    </p>
                  </div>
                  <span className="shrink-0 whitespace-nowrap text-xs text-neutral-500">
                    {relativeTime(e.created_at)}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
