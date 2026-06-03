import {
  ClipboardCheck,
  FileBarChart,
  FileText,
  Gauge,
  LayoutDashboard,
  ScrollText,
  Settings,
  ShieldAlert,
  Users,
  type LucideIcon,
} from "lucide-react";

export type NavItem = { label: string; href: string; icon: LucideIcon };

export const navItems: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Risk Profile", href: "/risk-profile", icon: ShieldAlert },
  { label: "Clients and Matters", href: "/clients", icon: Users },
  { label: "Compliance Program", href: "/compliance-program", icon: ClipboardCheck },
  { label: "Reporting", href: "/reporting", icon: FileBarChart },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Evaluation", href: "/evaluation", icon: Gauge },
  { label: "Audit Trail", href: "/audit-trail", icon: ScrollText },
  { label: "Settings", href: "/settings", icon: Settings },
];
