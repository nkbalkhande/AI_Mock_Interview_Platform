import { ROLE, type Role } from "@/lib/constants";

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
