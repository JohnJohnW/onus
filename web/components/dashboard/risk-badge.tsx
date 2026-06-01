import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const TONES: Record<string, string> = {
  low: "bg-emerald-500/15 text-emerald-400",
  medium: "bg-amber-500/15 text-amber-400",
  high: "bg-red-500/15 text-red-400",
  unassessed: "bg-neutral-500/15 text-neutral-300",
};

export function RiskBadge({ rating }: { rating: string }) {
  const key = (rating || "unassessed").toLowerCase();
  const tone = TONES[key] ?? TONES.unassessed;
  const label = key.charAt(0).toUpperCase() + key.slice(1);
  return (
    <Badge variant="outline" className={cn("border-transparent", tone)}>
      {label}
    </Badge>
  );
}
