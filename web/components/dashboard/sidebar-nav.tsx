"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { OnusMark } from "@/components/brand/onus-mark";
import { SignOutButton } from "@/components/sign-out-button";
import { cn } from "@/lib/utils";
import { navItems } from "./nav-items";

export function SidebarNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center gap-2 px-5">
        <OnusMark className="h-6 w-6 text-neutral-50" />
        <span className="text-lg font-semibold tracking-tight text-neutral-50">Onus</span>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
        {navItems.map(({ label, href, icon: Icon }) => {
          const active =
            href === "/dashboard"
              ? pathname === href
              : pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-neutral-800 text-neutral-50"
                  : "text-neutral-400 hover:bg-neutral-900 hover:text-neutral-100"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-neutral-800 p-3">
        <SignOutButton />
      </div>
    </div>
  );
}
