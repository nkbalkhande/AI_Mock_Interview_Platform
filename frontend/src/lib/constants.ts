export const APP_NAME =
  process.env.NEXT_PUBLIC_APP_NAME ?? "AI Mock Interview Platform";

/** Base path the browser uses for API calls (proxied to FastAPI by Next). */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/backend";

export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  forgotPassword: "/forgot-password",
  resetPassword: "/reset-password",
  candidate: {
    dashboard: "/dashboard",
    interviews: "/interviews",
    upcoming: "/upcoming-interviews",
    results: "/results",
    profile: "/profile",
  },
  admin: {
    dashboard: "/dashboard",
    users: "/users",
    interviews: "/interviews",
    assign: "/interviews/assign",
    evaluations: "/evaluations",
    roles: "/roles",
    notifications: "/notifications",
    profile: "/profile",
  },
} as const;

export const ROLE = {
  CANDIDATE: "CANDIDATE",
  INTERVIEWER: "INTERVIEWER",
  ADMIN: "ADMIN",
  SUPER_ADMIN: "SUPER_ADMIN",
} as const;

export type Role = (typeof ROLE)[keyof typeof ROLE];
