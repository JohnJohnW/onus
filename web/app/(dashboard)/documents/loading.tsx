import { Skeleton, SkeletonCard } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-8 space-y-3">
        <Skeleton className="h-8 w-44" />
        <Skeleton className="h-4 w-80" />
      </div>
      <div className="space-y-3">
        <SkeletonCard lines={1} />
        <SkeletonCard lines={1} />
      </div>
    </div>
  );
}
