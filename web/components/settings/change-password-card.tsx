"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const field =
  "rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

export function ChangePasswordCard() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    setErr(null);
    const res = await fetch("/api/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: current, new_password: next }),
    });
    setBusy(false);
    if (res.ok) {
      setMsg("Password changed.");
      setCurrent("");
      setNext("");
    } else {
      const d = await res.json().catch(() => null);
      setErr((d && d.detail) || "Could not change your password.");
    }
  }

  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="p-5">
        <form onSubmit={submit} className="space-y-2">
          <input
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            placeholder="Current password"
            className={`${field} w-full`}
          />
          <input
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            placeholder="New password (at least 12 characters)"
            className={`${field} w-full`}
          />
          <Button type="submit" size="sm" disabled={busy || !current || next.length < 12}>
            Change password
          </Button>
          {msg && <p className="text-xs text-emerald-400">{msg}</p>}
          {err && <p className="text-xs text-red-400">{err}</p>}
        </form>
      </CardContent>
    </Card>
  );
}
