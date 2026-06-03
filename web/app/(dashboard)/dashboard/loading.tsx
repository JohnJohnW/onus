import { Skeleton, SkeletonCard } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-10 space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
      </div>
      <Skeleton className="mb-8 h-16 w-full rounded-lg" />
      {["actions", "activity", "deadlines"].map((s) => (
        <div key={s} className="mb-10 space-y-3">
          <Skeleton className="h-3 w-32" />
          <SkeletonCard />
        </div>
      ))}
    </div>
  );
}
