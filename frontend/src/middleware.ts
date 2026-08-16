import { NextResponse, type NextRequest } from "next/server";

/**
 * UX-only session cookie check. Authoritative RBAC stays on FastAPI.
 *
 * Next.js 16.0.x ``src/proxy.ts`` 404s ``/login`` and ``/register`` in
 * ``next dev`` (home still works). ``middleware.ts`` does not have that bug.
 */
const PUBLIC_PATHS = [
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
];

const SESSION_COOKIE = "session";

export function middleware(request: NextRequest) {
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
