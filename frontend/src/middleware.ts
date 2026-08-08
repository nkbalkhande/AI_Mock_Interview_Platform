import { NextResponse, type NextRequest } from "next/server";

/**
 * Route protection at the edge.
 *
 * This is a lightweight guard: it checks for the presence of the auth session
 * cookie and redirects unauthenticated users away from protected areas.
 * Authoritative authorization (RBAC) is always enforced by the FastAPI backend
 * — the middleware only improves UX by avoiding flashes of protected pages.
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
  // Run on everything except Next internals, API routes and static assets.
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|images|icons).*)"],
};
