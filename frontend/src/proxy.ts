import { NextResponse, type NextRequest } from "next/server";

/**
 * Route protection at the network boundary (Next.js 16 ``proxy.ts``).
 *
 * Lightweight UX guard only: cookie presence, then redirect. Authoritative
 * RBAC stays on the FastAPI backend. Public auth pages are excluded from
 * the matcher — Next.js 16.0.x can 404 those routes in ``next dev`` when
 * this file intercepts them (``/`` still works; ``/login`` does not).
 */
const PUBLIC_PATHS = [
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
];

const SESSION_COOKIE = "session";

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );
  if (isPublic) {
    return NextResponse.next();
  }

  const hasSession = request.cookies.has(SESSION_COOKIE);
  if (!hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|images|icons|login|register|forgot-password|reset-password).*)",
  ],
};
