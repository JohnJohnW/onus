import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

// Public pages reachable without a session. /hosting is the demo data-residency /
// expression-of-interest page, which logged-out visitors must be able to see.
const PUBLIC_PATHS = ["/", "/login", "/signup", "/hosting"];

export default auth((req) => {
  const { pathname } = req.nextUrl;
  const isAuthed = !!req.auth;
  const isAuthPage = pathname === "/login" || pathname === "/signup";

  // Authenticated users shouldn't land on the login/signup pages.
  if (isAuthed && isAuthPage) {
    return NextResponse.redirect(new URL("/dashboard", req.nextUrl));
  }

  // Everything outside the public set requires a session.
  if (!isAuthed && !PUBLIC_PATHS.includes(pathname)) {
    return NextResponse.redirect(new URL("/login", req.nextUrl));
  }

  return NextResponse.next();
});

export const config = {
  // Run on page routes only - skip API routes, Next internals, and static files.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.).*)"],
};
