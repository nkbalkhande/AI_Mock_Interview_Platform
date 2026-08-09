import { ROLE, ROUTES, type Role } from "@/lib/constants";

/**
 * Minimal auth session shape shared across the app. The real token handling
 * lives in secure httpOnly cookies managed by the backend; the frontend only
 * needs to know the current user's identity/role for UI + route protection.
 */
export interface SessionUser {
  id: string;
  fullName: string;
  email: string;
  roles: Role[];
}

export function hasRole(user: SessionUser | null, role: Role): boolean {
  return !!user?.roles?.includes(role);
}

export function isAdmin(user: SessionUser | null): boolean {
  return (
    hasRole(user, ROLE.ADMIN) ||
    hasRole(user, ROLE.SUPER_ADMIN) ||
    hasRole(user, ROLE.INTERVIEWER)
  );
}

export function isCandidate(user: SessionUser | null): boolean {
  return hasRole(user, ROLE.CANDIDATE);
}

const ELEVATED_ROLES: readonly string[] = [
  ROLE.ADMIN,
  ROLE.SUPER_ADMIN,
  ROLE.INTERVIEWER,
];

/**
 * Post-login landing page based on RBAC roles: admins/interviewers go to the
 * admin dashboard, everyone else to the candidate dashboard.
 */
export function dashboardPathForRoles(roles: readonly string[]): string {
  const elevated = roles?.some((r) => ELEVATED_ROLES.includes(r));
  return elevated ? ROUTES.admin.dashboard : ROUTES.candidate.dashboard;
}
