import { Skeleton, SkeletonCard } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-8 space-y-3">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-4 w-72" />
      </div>
      <SkeletonCard lines={4} />
      <div className="mt-6">
        <SkeletonCard lines={2} />
      </div>
    </div>
  );
}
