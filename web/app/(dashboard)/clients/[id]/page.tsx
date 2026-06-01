import {
  ClientDetailView,
  type ClientDetail,
  type Indicator,
} from "@/components/clients/client-detail";
import { type CatalogueItem } from "@/components/clients/clients-list";
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

export default async function ClientDetailPage({ params }: { params: { id: string } }) {
  const session = await auth();
  const token = session?.access_token;
  if (!token) return null;

  const client = await getJson<ClientDetail | null>(`/clients/${params.id}`, token, null);
  if (!client) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Client not found</h1>
      </div>
    );
  }
  const [meta, indicators] = await Promise.all([
    getJson<{ designated_services: CatalogueItem[] }>("/clients/meta", token, {
      designated_services: [],
    }),
    getJson<Indicator[]>("/alerts/indicators", token, []),
  ]);

  return (
    <ClientDetailView
      client={client}
      services={meta.designated_services}
      indicators={indicators}
    />
  );
}
