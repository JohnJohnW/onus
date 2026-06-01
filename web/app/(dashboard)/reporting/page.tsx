import {
  ReportingView,
  type Report,
  type RetentionRecord,
} from "@/components/reporting/reporting-view";
import { auth } from "@/lib/auth";

const engineUrl = process.env.ENGINE_INTERNAL_URL ?? "http://localhost:8000";

async function getJson<T>(path: string, token: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${engineUrl}${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    return res.ok ? ((await res.json()) as T) : fallback;
  } catch {
    return fallback;
  }
}

export default async function ReportingPage() {
  const session = await auth();
  const token = session?.access_token;
  if (!token) return null;

  const [reports, records] = await Promise.all([
    getJson<Report[]>("/reports", token, []),
    getJson<RetentionRecord[]>("/records", token, []),
  ]);

  return <ReportingView reports={reports} records={records} />;
}
