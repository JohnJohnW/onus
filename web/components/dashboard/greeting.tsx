"use client";

import { useEffect, useState } from "react";

function greetingForHour(hour: number): string {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

/**
 * Time-of-day greeting computed from the user's local clock.
 *
 * The server renders in UTC, so the greeting can't be computed there. We start
 * from a deterministic "Hello" (matching on server and first client render to
 * avoid a hydration mismatch) and switch to the local-time greeting after mount.
 */
export function Greeting({ firstName }: { firstName: string }) {
  const [greeting, setGreeting] = useState("Hello");

  useEffect(() => {
    setGreeting(greetingForHour(new Date().getHours()));
  }, []);

  return (
    <h1 className="text-2xl font-semibold tracking-tight">
      {greeting}, {firstName}.
    </h1>
  );
}
