import { ChangePasswordCard } from "@/components/settings/change-password-card";
import { GovernancePanel } from "@/components/settings/governance-panel";
import { SanctionsPanel } from "@/components/settings/sanctions-panel";
import { SettingsForm } from "@/components/settings/settings-form";
import { UsersPanel } from "@/components/settings/users-panel";
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
  users: { id: string; email: string; full_name: string | null; role: string; is_active?: boolean }[];
  governance_roles: {
    id: string;
    role: string;
    user_id: string | null;
    is_active: boolean;
    management_level: boolean;
    is_australian_resident: boolean;
    fit_and_proper_considered: boolean;
    qualifies_reason: string | null;
  }[];
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

  if (!session || !data) {
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
              {firm.austrac_enrolment_number ? ` - ${firm.austrac_enrolment_number}` : ""}
            </span>
          </CardContent>
        </Card>
      </section>

      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">Users</h2>
        <UsersPanel
          users={users}
          isAdmin={session.role === "admin"}
          currentUserId={session.user_id}
        />
      </section>

      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Your account
        </h2>
        <ChangePasswordCard />
      </section>

      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Governance roles
        </h2>
        <GovernancePanel users={users} roles={governance_roles} />
      </section>

      <section>
        <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-neutral-500">
          Sanctions screening
        </h2>
        <SanctionsPanel />
      </section>
    </div>
  );
}
