import { Skeleton, SkeletonCard } from "@/components/ui/skeleton";

// Generic fallback skeleton for any dashboard page without its own loading.tsx.
export default function Loading() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-10 space-y-3">
        <Skeleton className="h-7 w-56" />
        <Skeleton className="h-4 w-72" />
      </div>
      <div className="space-y-4">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    </div>
  );
}
