import { Card, CardContent } from "@/components/ui/card";

export function ComingSoon({ title, description }: { title: string; description: string }) {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-sm text-neutral-400">{description}</p>
      <Card className="mt-8 border-neutral-800 bg-neutral-900/30">
        <CardContent className="p-6 text-sm text-neutral-400">
          This section is coming soon. Onus is building it out.
        </CardContent>
      </Card>
    </div>
  );
}
