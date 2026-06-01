import {
  ClientsList,
  type CatalogueItem,
  type ClientListItem,
} from "@/components/clients/clients-list";
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

export default async function ClientsPage() {
  const session = await auth();
  const token = session?.access_token;
  if (!token) return null;

  const [clients, meta] = await Promise.all([
    getJson<ClientListItem[]>("/clients", token, []),
    getJson<{ customer_types: CatalogueItem[] }>("/clients/meta", token, { customer_types: [] }),
  ]);

  return <ClientsList clients={clients} customerTypes={meta.customer_types} />;
}
