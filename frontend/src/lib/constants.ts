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
    interviewsJdBased: "/interviews/jd-based",
    interviewsRoleBased: "/interviews/role-based",
    upcoming: "/upcoming-interviews",
    upcomingDetail: (interviewId: string) =>
      `/upcoming-interviews/${interviewId}`,
    results: "/results",
    practiceResult: (sessionId: string) =>
      `/results/practice/${sessionId}`,
    assignedResult: (sessionId: string) =>
      `/results/assigned/${sessionId}`,
    interview: (sessionId: string) => `/interview/${sessionId}`,
    profile: "/profile",
  },
  admin: {
    dashboard: "/admin/dashboard",
    users: "/admin/users",
    interviews: "/admin/interviews",
    assign: "/admin/interviews/assign",
    evaluations: "/admin/evaluations",
    roles: "/admin/roles",
    notifications: "/admin/notifications",
    profile: "/admin/profile",
  },
} as const;

export const ROLE = {
  CANDIDATE: "CANDIDATE",
  INTERVIEWER: "INTERVIEWER",
  ADMIN: "ADMIN",
  SUPER_ADMIN: "SUPER_ADMIN",
} as const;

export type Role = (typeof ROLE)[keyof typeof ROLE];
