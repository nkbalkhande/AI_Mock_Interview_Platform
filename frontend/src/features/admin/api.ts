import { apiClient } from "@/lib/api-client";

import type {
  AdminDashboardResponse,
  AssignInterviewRequest,
  AssignInterviewResponse,
  EvaluationDetailResponse,
  EvaluationListResponse,
  InterviewDetailResponse,
  InterviewListResponse,
  JobRoleItem,
  SubmitDecisionResponse,
  UpdateUserStatusResponse,
  UserDetailResponse,
  UserListResponse,
} from "./types";

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export async function getAdminDashboard(): Promise<AdminDashboardResponse> {
  const { data } = await apiClient.get<AdminDashboardResponse>(
    "/admin/dashboard",
  );
  return data;
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export async function getUsers(params: {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  is_active?: boolean;
}): Promise<UserListResponse> {
  const { data } = await apiClient.get<UserListResponse>("/admin/users", {
    params,
  });
  return data;
}

export async function getUserDetail(
  userId: string,
  params?: { page?: number; page_size?: number },
): Promise<UserDetailResponse> {
  const { data } = await apiClient.get<UserDetailResponse>(
    `/admin/users/${userId}`,
    { params },
  );
  return data;
}

export async function updateUserStatus(
  userId: string,
  isActive: boolean,
): Promise<UpdateUserStatusResponse> {
  const { data } = await apiClient.patch<UpdateUserStatusResponse>(
    `/admin/users/${userId}/status`,
    { is_active: isActive },
  );
  return data;
}

// ---------------------------------------------------------------------------
// Interviews
// ---------------------------------------------------------------------------

export async function getInterviews(params: {
  page?: number;
  page_size?: number;
  status?: string;
  interview_type?: string;
  search?: string;
}): Promise<InterviewListResponse> {
  const { data } = await apiClient.get<InterviewListResponse>(
    "/admin/interviews",
    { params },
  );
  return data;
}

export async function getInterviewDetail(
  interviewId: string,
): Promise<InterviewDetailResponse> {
  const { data } = await apiClient.get<InterviewDetailResponse>(
    `/admin/interviews/${interviewId}`,
  );
  return data;
}

export async function assignInterview(
  request: AssignInterviewRequest,
): Promise<AssignInterviewResponse> {
  const { data } = await apiClient.post<AssignInterviewResponse>(
    "/admin/interviews/assign",
    request,
  );
  return data;
}

export async function cancelInterview(
  interviewId: string,
): Promise<InterviewDetailResponse> {
  const { data } = await apiClient.patch<InterviewDetailResponse>(
    `/admin/interviews/${interviewId}/cancel`,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Evaluations
// ---------------------------------------------------------------------------

export async function getEvaluations(params: {
  page?: number;
  page_size?: number;
  review_state?: string;
}): Promise<EvaluationListResponse> {
  const { data } = await apiClient.get<EvaluationListResponse>(
    "/admin/evaluations",
    { params },
  );
  return data;
}

export async function getEvaluationDetail(
  sessionId: string,
): Promise<EvaluationDetailResponse> {
  const { data } = await apiClient.get<EvaluationDetailResponse>(
    `/admin/evaluations/${sessionId}`,
  );
  return data;
}

export async function submitDecision(
  sessionId: string,
  request: { admin_decision: string; admin_feedback?: string | null },
): Promise<SubmitDecisionResponse> {
  const { data } = await apiClient.post<SubmitDecisionResponse>(
    `/admin/evaluations/${sessionId}/decision`,
    request,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Job Roles
// ---------------------------------------------------------------------------

export async function getJobRoles(): Promise<JobRoleItem[]> {
  const { data } = await apiClient.get<JobRoleItem[]>("/admin/job-roles");
  return data;
}
