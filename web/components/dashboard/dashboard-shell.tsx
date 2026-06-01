"use client";

import { Menu } from "lucide-react";
import { useState } from "react";

import { OnusMark } from "@/components/brand/onus-mark";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { SidebarNav } from "./sidebar-nav";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-neutral-950 text-neutral-100">
      {/* Desktop: persistent sidebar */}
      <aside className="hidden w-64 shrink-0 border-r border-neutral-800 md:block">
        <div className="sticky top-0 h-screen">
          <SidebarNav />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile: top bar with collapsible sidebar */}
        <header className="flex h-14 items-center gap-2 border-b border-neutral-800 px-3 md:hidden">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Open navigation">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent
              side="left"
              className="w-64 border-neutral-800 bg-neutral-950 p-0 text-neutral-100"
            >
              <SheetTitle className="sr-only">Navigation</SheetTitle>
              <SidebarNav onNavigate={() => setOpen(false)} />
            </SheetContent>
          </Sheet>
          <OnusMark className="h-5 w-5" />
          <span className="text-base font-semibold tracking-tight">Onus</span>
        </header>

        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
