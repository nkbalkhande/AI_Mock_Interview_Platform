"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";

import { useMe } from "@/features/auth/hooks";
import { useAuth } from "@/hooks/use-auth";
import { isAdmin, isCandidate, dashboardPathForRoles } from "@/lib/auth";
import { ROUTES } from "@/lib/constants";

/**
 * Boots the client-side auth session for any authenticated area.
 *
 * Two things happen here beyond ``useMe``'s implicit store hydration:
 *  1. If ``/auth/me`` reports no user (401), route the browser to /login —
 *     the middleware also does this on the initial navigation but a stale
 *     cookie can still let a page render before the query resolves.
 *  2. If ``requireRole`` doesn't match the resolved user's roles, redirect
 *     to the correct dashboard rather than showing the wrong shell.
 *
 * Rendering children happens optimistically; the API calls the layout makes
 * (dashboard, notifications) will individually 401 on their own if the
 * session is truly gone, but that's rare in practice compared to the more
 * common "refresh after login" flow which works out of the box.
 */
export function SessionBootstrap({
  requireRole,
  children,
}: {
  requireRole: "candidate" | "admin";
  children: ReactNode;
}) {
  const { data, isFetched, isError } = useMe();
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isFetched) return;

    if (data === null || isError) {
      router.replace(ROUTES.login);
      return;
    }

    if (!user) return;

    if (requireRole === "candidate" && !isCandidate(user) && isAdmin(user)) {
      router.replace(dashboardPathForRoles(user.roles));
    } else if (requireRole === "admin" && !isAdmin(user)) {
      router.replace(dashboardPathForRoles(user.roles));
    }
  }, [data, isFetched, isError, requireRole, router, user]);

  return <>{children}</>;
}
