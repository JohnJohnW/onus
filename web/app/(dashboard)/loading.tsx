import { Spinner } from "@/components/ui/spinner";

// Shown automatically during navigation to any dashboard page while the server renders
// it (which can wait on the engine). Gives instant, subtle feedback so a slow page reads
// as loading, not stuck.
export default function Loading() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="flex items-center gap-2 text-sm text-neutral-500">
        <Spinner className="h-4 w-4" />
        <span>Loading...</span>
      </div>
    </div>
  );
}
