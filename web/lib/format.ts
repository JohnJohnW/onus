/** Human-friendly relative time, e.g. "2 hours ago". */
export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diffMs = Math.max(0, Date.now() - then);
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} minute${mins === 1 ? "" : "s"} ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} day${days === 1 ? "" : "s"} ago`;
  const months = Math.floor(days / 30);
  return `${months} month${months === 1 ? "" : "s"} ago`;
}

/** Australian-style date, e.g. "9 Jun 2026". */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** Tailwind text colour for a days-remaining value: red <14, amber <30, green >=30. */
export function daysRemainingTone(days: number | null): string {
  if (days === null) return "text-neutral-400";
  if (days < 14) return "text-red-400";
  if (days < 30) return "text-amber-400";
  return "text-emerald-400";
}

/** Human label for a days-remaining value. */
export function daysRemainingLabel(days: number | null): string {
  if (days === null) return "";
  if (days < 0) {
    const n = Math.abs(days);
    return `${n} day${n === 1 ? "" : "s"} overdue`;
  }
  if (days === 0) return "Due today";
  return `${days} day${days === 1 ? "" : "s"} left`;
}
