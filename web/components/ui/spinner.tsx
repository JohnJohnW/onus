import { cn } from "@/lib/utils";

// A small, subtle loading spinner. Inherits the current text color, so it sits cleanly
// inside buttons (use mr-2 before label text) or standalone in a loading state.
export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn("inline-block h-3.5 w-3.5 animate-spin", className)}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z" />
    </svg>
  );
}
