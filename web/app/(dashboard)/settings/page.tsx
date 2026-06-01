import { SettingsForm } from "@/components/settings/settings-form";
import { Card, CardContent } from "@/components/ui/card";
import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

type Firm = {
  id: string;
  name: string;
  abn: string | null;
  firm_size: string | null;
  enrolment_status: string;
  austrac_enrolment_number: string | null;
};
type SettingsData = {
  firm: Firm;
  users: { id: string; email: string; full_name: string | null; role: string }[];
  governance_roles: { id: string; role: string; is_active: boolean }[];
};

async function getSettings(token: string, firmId: string): Promise<SettingsData | null> {
  try {
    const res = await fetch(`${engineUrl}/firms/${firmId}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as SettingsData) : null;
  } catch {
    return null;
  }
}

function titleize(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default async function SettingsPage() {
  const session = await auth();
  const data =
    session?.access_token && session?.firm_id
      ? await getSettings(session.access_token, session.firm_id)
      : null;

  if (!data) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-2 text-sm text-neutral-400">Could not load your settings right now.</p>
      </div>
    );
  }

  const { firm, users, governance_roles } = data;

  return (
    <div className="mx-auto max-w-3xl space-y-10 px-6 py-10">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-2 text-sm text-neutral-400">Firm details, users, and governance.</p>
      </div>

      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Firm details
        </h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="p-6">
            <SettingsForm firm={firm} />
          </CardContent>
        </Card>
      </section>

      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          AML/CTF enrolment
        </h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="flex items-center justify-between gap-4 p-5 text-sm">
            <span className="text-neutral-300">AUSTRAC enrolment</span>
            <span className="text-neutral-100">
              {titleize(firm.enrolment_status)}
              {firm.austrac_enrolment_number ? ` · ${firm.austrac_enrolment_number}` : ""}
            </span>
          </CardContent>
        </Card>
      </section>

      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">Users</h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="divide-y divide-neutral-800 p-0">
            {users.map((u) => (
              <div key={u.id} className="flex items-center justify-between gap-4 px-5 py-4">
                <div className="min-w-0">
                  <p className="truncate text-sm text-neutral-200">{u.full_name ?? u.email}</p>
                  <p className="truncate text-xs text-neutral-500">{u.email}</p>
                </div>
                <span className="shrink-0 text-xs capitalize text-neutral-400">{u.role}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Governance roles
        </h2>
        <Card className="border-neutral-800 bg-neutral-900/50">
          <CardContent className="divide-y divide-neutral-800 p-0">
            {governance_roles.map((r) => (
              <div key={r.id} className="flex items-center justify-between gap-4 px-5 py-4">
                <span className="text-sm text-neutral-200">{titleize(r.role)}</span>
                <span
                  className={
                    r.is_active ? "text-xs text-emerald-400" : "text-xs text-neutral-500"
                  }
                >
                  {r.is_active ? "Active" : "Inactive"}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
