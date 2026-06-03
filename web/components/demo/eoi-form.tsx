"use client";

import { useState } from "react";

const field =
  "w-full rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 outline-none focus:border-neutral-600";

export function EoiForm() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [firm, setFirm] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
      setErr("Enter a valid email address.");
      return;
    }
    setBusy(true);
    const res = await fetch("/api/eoi", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: email.trim(),
        name: name.trim() || null,
        firm_name: firm.trim() || null,
        note: note.trim() || null,
      }),
    });
    setBusy(false);
    if (res.ok) {
      setDone(true);
    } else {
      const d = await res.json().catch(() => null);
      setErr((d && d.detail) || "Could not submit right now. Please try again.");
    }
  }

  if (done) {
    return (
      <p className="rounded-md border border-emerald-900/50 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-300">
        Thanks - we&apos;ll be in touch about an Australian-hosted deployment.
      </p>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="eoi-name" className="mb-1 block text-xs text-neutral-400">
            Your name (optional)
          </label>
          <input id="eoi-name" value={name} onChange={(e) => setName(e.target.value)} className={field} />
        </div>
        <div>
          <label htmlFor="eoi-firm" className="mb-1 block text-xs text-neutral-400">
            Firm (optional)
          </label>
          <input id="eoi-firm" value={firm} onChange={(e) => setFirm(e.target.value)} className={field} />
        </div>
      </div>
      <div>
        <label htmlFor="eoi-email" className="mb-1 block text-xs text-neutral-400">
          Email
        </label>
        <input
          id="eoi-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className={field}
        />
      </div>
      <div>
        <label htmlFor="eoi-note" className="mb-1 block text-xs text-neutral-400">
          Anything you want us to know (optional)
        </label>
        <textarea id="eoi-note" value={note} onChange={(e) => setNote(e.target.value)} rows={2} className={field} />
      </div>
      {err && <p className="text-sm text-red-400">{err}</p>}
      <button
        type="submit"
        disabled={busy}
        className="rounded-md bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 transition hover:bg-white disabled:opacity-50"
      >
        {busy ? "Submitting..." : "Register interest"}
      </button>
    </form>
  );
}
