import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// Base skeleton block. Pages compose these in their loading.tsx so a navigation shows an
// instant placeholder that mirrors the real layout, instead of a blank wait.
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-neutral-800/80", className)} />;
}

// A card-shaped placeholder matching the real content cards (border + dark surface).
export function SkeletonCard({ lines = 2 }: { lines?: number }) {
  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="space-y-3 p-5">
        <Skeleton className="h-4 w-1/3" />
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className={cn("h-3", i % 2 ? "w-1/2" : "w-2/3")} />
        ))}
      </CardContent>
    </Card>
  );
}
