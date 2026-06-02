"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type U = { id: string; email: string; full_name: string | null; role: string; is_active?: boolean };

const field =
  "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

export function UsersPanel({
  users,
  isAdmin,
  currentUserId,
}: {
  users: U[];
  isAdmin: boolean;
  currentUserId: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [tempPw, setTempPw] = useState<string | null>(null);
  const [form, setForm] = useState({ full_name: "", email: "", role: "member" });

  async function addUser(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    setTempPw(null);
    const res = await fetch("/api/firm/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    });
    setBusy(false);
    if (res.ok) {
      const d = await res.json();
      setTempPw(d.temporary_password);
      setForm({ full_name: "", email: "", role: "member" });
      router.refresh();
    } else {
      const d = await res.json().catch(() => null);
      setErr((d && d.detail) || "Could not add the user.");
    }
  }

  async function patchUser(id: string, body: Record<string, unknown>) {
    setBusy(true);
    setErr(null);
    const res = await fetch(`/api/firm/users/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setBusy(false);
    if (res.ok) router.refresh();
    else {
      const d = await res.json().catch(() => null);
      setErr((d && d.detail) || "Could not update the user.");
    }
  }

  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="divide-y divide-neutral-800 p-0">
        {users.map((u) => (
          <div key={u.id} className="flex items-center justify-between gap-4 px-5 py-4">
            <div className="min-w-0">
              <p className="truncate text-sm text-neutral-200">
                {u.full_name ?? u.email}
                {u.is_active === false && <span className="ml-2 text-xs text-neutral-500">(deactivated)</span>}
              </p>
              <p className="truncate text-xs text-neutral-500">{u.email}</p>
            </div>
            {isAdmin && u.id !== currentUserId ? (
              <div className="flex shrink-0 items-center gap-3">
                <select
                  value={u.role}
                  disabled={busy}
                  onChange={(e) => patchUser(u.id, { role: e.target.value })}
                  className={field}
                  aria-label="Role"
                >
                  <option value="admin">admin</option>
                  <option value="member">member</option>
                </select>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => patchUser(u.id, { is_active: u.is_active === false })}
                  className="whitespace-nowrap text-xs text-neutral-500 hover:text-neutral-200"
                >
                  {u.is_active === false ? "Reactivate" : "Deactivate"}
                </button>
              </div>
            ) : (
              <span className="shrink-0 text-xs capitalize text-neutral-400">
                {u.role}
                {u.id === currentUserId ? " (you)" : ""}
              </span>
            )}
          </div>
        ))}

        {isAdmin && (
          <form onSubmit={addUser} className="space-y-2 px-5 py-4">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Add a colleague</p>
            <div className="grid gap-2 sm:grid-cols-3">
              <input
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="Full name"
                className={field}
              />
              <input
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="Email"
                className={field}
              />
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                className={field}
                aria-label="New user role"
              >
                <option value="member">member</option>
                <option value="admin">admin</option>
              </select>
            </div>
            <Button type="submit" size="sm" disabled={busy || !form.full_name.trim() || !form.email.trim()}>
              Add user
            </Button>
            {tempPw && (
              <p className="text-xs text-emerald-400">
                Temporary password (share securely, shown once):{" "}
                <span className="font-mono text-neutral-100">{tempPw}</span>
              </p>
            )}
            {err && <p className="text-xs text-red-400">{err}</p>}
          </form>
        )}
      </CardContent>
    </Card>
  );
}
