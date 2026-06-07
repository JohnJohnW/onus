import { AlertCircle, AlertTriangle, CheckCircle2, Info, type LucideIcon } from "lucide-react";

// Single source of truth for severity styling across every AI surface and risk badge.
// Replaces the four ad-hoc colour maps that used to live in review-result, risk-profile-view,
// risk-badge and client-detail.
export type Severity = "high" | "medium" | "low" | "info" | "unassessed";

type SeverityToken = {
  label: string;
  chip: string; // border + bg + text for a small pill
  rail: string; // left-border accent for a finding card
  tintBg: string; // faint card tint (used for high only)
  dot: string; // solid dot
  ring: string; // soft ring background behind the verdict icon
  text: string; // icon / accent text colour
  Icon: LucideIcon;
};

export const SEVERITY: Record<Severity, SeverityToken> = {
  high: {
    label: "High",
    chip: "border-red-500/30 bg-red-500/10 text-red-300",
    rail: "border-l-red-500/60",
    tintBg: "bg-red-500/[0.06]",
    dot: "bg-red-500",
    ring: "bg-red-500/15",
    text: "text-red-400",
    Icon: AlertTriangle,
  },
  medium: {
    label: "Medium",
    chip: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    rail: "border-l-amber-500/50",
    tintBg: "bg-transparent",
    dot: "bg-amber-500",
    ring: "bg-amber-500/15",
    text: "text-amber-400",
    Icon: AlertCircle,
  },
  low: {
    label: "Low",
    chip: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    rail: "border-l-emerald-500/40",
    tintBg: "bg-transparent",
    dot: "bg-emerald-500",
    ring: "bg-emerald-500/15",
    text: "text-emerald-400",
    Icon: CheckCircle2,
  },
  info: {
    label: "Info",
    chip: "border-neutral-600/40 bg-neutral-700/20 text-neutral-300",
    rail: "border-l-neutral-700",
    tintBg: "bg-transparent",
    dot: "bg-neutral-500",
    ring: "bg-neutral-700/40",
    text: "text-neutral-400",
    Icon: Info,
  },
  unassessed: {
    label: "Unassessed",
    chip: "border-neutral-600/40 bg-neutral-700/20 text-neutral-300",
    rail: "border-l-neutral-700",
    tintBg: "bg-transparent",
    dot: "bg-neutral-500",
    ring: "bg-neutral-700/40",
    text: "text-neutral-400",
    Icon: Info,
  },
};

export const SEVERITY_ORDER: Record<Severity, number> = {
  high: 0,
  medium: 1,
  low: 2,
  info: 3,
  unassessed: 4,
};

export function severityOf(value: string | null | undefined): Severity {
  const v = (value || "").toLowerCase();
  return (v in SEVERITY ? v : "unassessed") as Severity;
}
