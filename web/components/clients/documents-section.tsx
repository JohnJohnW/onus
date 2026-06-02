"use client";

import { useCallback, useEffect, useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { formatDate } from "@/lib/format";

type Doc = {
  id: string;
  filename: string;
  content_type: string | null;
  size_bytes: number;
  created_at: string;
};

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentsSection({ entityType, entityId }: { entityType: string; entityId: string }) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    const res = await fetch(`/api/documents?entity_type=${entityType}&entity_id=${entityId}`, {
      cache: "no-store",
    });
    if (res.ok) setDocs(await res.json());
  }, [entityType, entityId]);

  useEffect(() => {
    load();
  }, [load]);

  async function upload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setErr(null);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("entity_type", entityType);
    fd.append("entity_id", entityId);
    const res = await fetch("/api/documents", { method: "POST", body: fd });
    setBusy(false);
    e.target.value = "";
    if (res.ok) {
      load();
    } else {
      const d = await res.json().catch(() => null);
      setErr((d && d.detail) || "Upload failed.");
    }
  }

  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="space-y-3 p-5 text-sm">
        {docs.length === 0 ? (
          <p className="text-neutral-500">No documents attached.</p>
        ) : (
          <div className="divide-y divide-neutral-800">
            {docs.map((d) => (
              <div key={d.id} className="flex items-center justify-between gap-3 py-2">
                <div className="min-w-0">
                  <p className="truncate text-neutral-200">{d.filename}</p>
                  <p className="text-xs text-neutral-500">
                    {humanSize(d.size_bytes)} - {formatDate(d.created_at)}
                  </p>
                </div>
                <a
                  href={`/api/documents/${d.id}/download`}
                  className="shrink-0 text-xs text-neutral-400 hover:text-neutral-200"
                >
                  Download
                </a>
              </div>
            ))}
          </div>
        )}
        <div className="flex flex-wrap items-center gap-3 border-t border-neutral-800 pt-3">
          <span className="text-xs text-neutral-400">Attach evidence (ID, verification, signed approval):</span>
          <input
            type="file"
            onChange={upload}
            disabled={busy}
            aria-label="Upload a document"
            className="text-xs text-neutral-300 file:mr-2 file:rounded file:border-0 file:bg-neutral-800 file:px-2 file:py-1 file:text-neutral-200"
          />
        </div>
        {err && <p className="text-xs text-red-400">{err}</p>}
        <p className="text-xs text-neutral-600">
          PDF, image, or office file up to 20 MB. Retained for the 7-year period.
        </p>
      </CardContent>
    </Card>
  );
}
