"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";

const FIRM_SIZES = ["Sole practitioner", "2-5", "6-20", "21-50", "50+"];

type Firm = { name: string; abn: string | null; firm_size: string | null };

export function SettingsForm({ firm }: { firm: Firm }) {
  const router = useRouter();
  const [name, setName] = useState(firm.name ?? "");
  const [abn, setAbn] = useState(firm.abn ?? "");
  const [firmSize, setFirmSize] = useState(firm.firm_size ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    const res = await fetch("/api/firm", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, abn, firm_size: firmSize }),
    });
    setBusy(false);
    if (res.ok) {
      setMessage("Saved.");
      router.refresh();
    } else {
      setMessage("Could not save. Please try again.");
    }
  }

  const field =
    "w-full rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";
  const label = "mb-1 block text-sm text-neutral-400";

  return (
    <form onSubmit={save} className="space-y-4">
      <div>
        <label htmlFor="name" className={label}>Firm name</label>
        <input id="name" value={name} onChange={(e) => setName(e.target.value)} className={field} />
      </div>
      <div>
        <label htmlFor="abn" className={label}>ABN</label>
        <input id="abn" value={abn} onChange={(e) => setAbn(e.target.value)} className={field} />
      </div>
      <div>
        <label htmlFor="firmSize" className={label}>Firm size</label>
        <select id="firmSize" value={firmSize} onChange={(e) => setFirmSize(e.target.value)} className={field}>
          <option value="">Select...</option>
          {FIRM_SIZES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-3">
        <Button type="submit" size="sm" disabled={busy}>
          {busy ? "Saving..." : "Save changes"}
        </Button>
        {message && <span className="text-xs text-neutral-400">{message}</span>}
      </div>
    </form>
  );
}
