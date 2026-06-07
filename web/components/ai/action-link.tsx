"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

// A finding's "now do this" control. Three modes:
//  - navigate: go to an existing in-app route (next/link)
//  - call: POST/PATCH an existing API proxy, then refresh (e.g. approve, re-run, save)
//  - done: a local acknowledge tick (no server effect)
// URLs/methods are always supplied by client code, never by model output - the model only
// chooses a symbolic key that client code maps to one of these.
export type AiAction = {
  mode: "navigate" | "call" | "done";
  label: string;
  href?: string;
  endpoint?: string;
  method?: string;
  body?: unknown;
  doneLabel?: string;
};

export function ActionLink({ action }: { action: AiAction }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [state, setState] = useState<"idle" | "ok" | "err">("idle");
  const [msg, setMsg] = useState<string | null>(null);

  if (action.mode === "navigate" && action.href) {
    return (
      <Button asChild size="sm" variant="outline">
        <Link href={action.href}>{action.label}</Link>
      </Button>
    );
  }

  if (action.mode === "done") {
    return (
      <Button size="sm" variant="outline" disabled={state === "ok"} onClick={() => setState("ok")}>
        {state === "ok" ? (action.doneLabel ?? "Done") : action.label}
      </Button>
    );
  }

  async function run() {
    if (!action.endpoint) return;
    setBusy(true);
    setMsg(null);
    try {
      const res = await fetch(action.endpoint, {
        method: action.method ?? "POST",
        headers: action.body ? { "Content-Type": "application/json" } : undefined,
        body: action.body ? JSON.stringify(action.body) : undefined,
      });
      if (res.ok) {
        setState("ok");
        setMsg(action.doneLabel ?? "Done");
        router.refresh();
      } else {
        setState("err");
        const d = await res.json().catch(() => null);
        setMsg((d && d.detail) || "That did not work. Please try again.");
      }
    } catch {
      setState("err");
      setMsg("That did not work. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="inline-flex items-center gap-2">
      <Button size="sm" variant="outline" disabled={busy || state === "ok"} onClick={run}>
        {busy ? (
          <>
            <Spinner className="mr-2" />
            Working...
          </>
        ) : state === "ok" ? (
          (action.doneLabel ?? "Done")
        ) : (
          action.label
        )}
      </Button>
      {msg && (
        <span className={state === "err" ? "text-xs text-red-400" : "text-xs text-emerald-400"}>{msg}</span>
      )}
    </span>
  );
}
