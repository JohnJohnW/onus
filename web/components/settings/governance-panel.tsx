"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type User = { id: string; email: string; full_name: string | null };
type Role = {
  id: string;
  role: string;
  user_id: string | null;
  management_level: boolean;
  is_australian_resident: boolean;
  fit_and_proper_considered: boolean;
  qualifies_reason: string | null;
};

const ROLE_DEFS = [
  { key: "governing_body", label: "Governing body", hint: "Oversees the program" },
  { key: "senior_manager", label: "Senior manager", hint: "Approves the program (Act s26P)" },
  {
    key: "compliance_officer",
    label: "AML/CTF compliance officer",
    hint: "Must be management level, an Australian resident, and fit & proper (Act s26J)",
  },
  {
    key: "independent_evaluator",
    label: "Independent evaluator",
    hint: "Cannot be the compliance officer (Step 5)",
  },
];

const field =
  "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

function RoleRow({
  def,
  role,
  users,
}: {
  def: { key: string; label: string; hint: string };
  role: Role | undefined;
  users: User[];
}) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [userId, setUserId] = useState(role?.user_id ?? users[0]?.id ?? "");
  const [reason, setReason] = useState(role?.qualifies_reason ?? "");
  const [elig, setElig] = useState({
    management_level: role?.management_level ?? false,
    is_australian_resident: role?.is_australian_resident ?? false,
    fit_and_proper_considered: role?.fit_and_proper_considered ?? false,
  });
  const isCO = def.key === "compliance_officer";
  const holder = role?.user_id ? users.find((u) => u.id === role.user_id) : null;

  async function assign() {
    if (!userId) return;
    setBusy(true);
    setError("");
    const res = await fetch("/api/governance/assign", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: def.key, user_id: userId, qualifies_reason: reason || null, ...elig }),
    });
    setBusy(false);
    if (res.ok) {
      setOpen(false);
      router.refresh();
    } else {
      const d = await res.json().catch(() => ({}));
      setError(d.detail || "Could not assign this role.");
    }
  }

  return (
    <div className="px-5 py-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm text-neutral-200">{def.label}</p>
          <p className="mt-0.5 text-xs text-neutral-500">
            {holder ? (holder.full_name ?? holder.email) : "Unassigned"} - {def.hint}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="shrink-0 text-xs text-neutral-500 hover:text-neutral-300"
        >
          {open ? "Close" : holder ? "Change" : "Assign"}
        </button>
      </div>
      {open && (
        <div className="mt-3 space-y-2">
          <select value={userId} onChange={(e) => setUserId(e.target.value)} className={`${field} w-full`}>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name ? `${u.full_name} (${u.email})` : u.email}
              </option>
            ))}
          </select>
          {isCO && (
            <div className="flex flex-col gap-1.5 text-sm text-neutral-300">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={elig.management_level}
                  onChange={(e) => setElig({ ...elig, management_level: e.target.checked })}
                />
                At management level
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={elig.is_australian_resident}
                  onChange={(e) => setElig({ ...elig, is_australian_resident: e.target.checked })}
                />
                Australian resident
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={elig.fit_and_proper_considered}
                  onChange={(e) =>
                    setElig({ ...elig, fit_and_proper_considered: e.target.checked })
                  }
                />
                Fit-and-proper considered (competence, character, conflicts)
              </label>
            </div>
          )}
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Why do they qualify? (optional note)"
            className={`${field} w-full`}
          />
          <div className="flex items-center gap-3">
            <Button size="sm" disabled={busy} onClick={assign}>
              {busy ? "Saving..." : "Save"}
            </Button>
            {error && <span className="text-xs text-red-400">{error}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

export function GovernancePanel({ users, roles }: { users: User[]; roles: Role[] }) {
  const byRole: Record<string, Role> = {};
  for (const r of roles) byRole[r.role] = r;
  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="divide-y divide-neutral-800 p-0">
        {ROLE_DEFS.map((def) => (
          <RoleRow key={def.key} def={def} role={byRole[def.key]} users={users} />
        ))}
      </CardContent>
    </Card>
  );
}
