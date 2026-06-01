"use client";

import { LogOut } from "lucide-react";
import { signOut } from "next-auth/react";

export function SignOutButton() {
  return (
    <button
      onClick={() => signOut({ redirectTo: "/login" })}
      className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-neutral-400 transition-colors hover:bg-neutral-900 hover:text-neutral-100"
    >
      <LogOut className="h-4 w-4 shrink-0" />
      Sign out
    </button>
  );
}
