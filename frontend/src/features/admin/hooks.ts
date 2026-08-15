"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  assignInterview,
  cancelInterview,
  getAdminDashboard,
  getEvaluationDetail,
  getEvaluations,
  getInterviewDetail,
  getInterviews,
  getJobRoles,
  getUserDetail,
  getUsers,
  rescheduleInterview,
  submitDecision,
  updateUserStatus,
} from "./api";
import type {
  AdminDashboardResponse,
  AssignInterviewRequest,
  AssignInterviewResponse,
  EvaluationDetailResponse,
  EvaluationListResponse,
  InterviewDetailResponse,
  InterviewListResponse,
  RescheduleInterviewRequest,
  RescheduleInterviewResponse,
  JobRoleItem,
  SubmitDecisionResponse,
  UpdateUserStatusResponse,
  UserDetailResponse,
  UserListResponse,
} from "./types";
import type { ApiError } from "@/features/auth/types";

export const adminKeys = {
  all: ["admin"] as const,
  dashboard: () => [...adminKeys.all, "dashboard"] as const,
  users: (params: Record<string, unknown>) =>
    [...adminKeys.all, "users", params] as const,
  userDetail: (id: string, params: Record<string, unknown> = {}) =>
    [...adminKeys.all, "user-detail", id, params] as const,
  interviews: (params: Record<string, unknown>) =>
    [...adminKeys.all, "interviews", params] as const,
  interviewDetail: (id: string) =>
    [...adminKeys.all, "interview-detail", id] as const,
  evaluations: (params: Record<string, unknown>) =>
    [...adminKeys.all, "evaluations", params] as const,
  evaluationDetail: (id: string) =>
    [...adminKeys.all, "evaluation-detail", id] as const,
  jobRoles: () => [...adminKeys.all, "job-roles"] as const,
};

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export function useAdminDashboard() {
  return useQuery<AdminDashboardResponse, ApiError>({
    queryKey: adminKeys.dashboard(),
    queryFn: getAdminDashboard,
  });
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export function useUsers(params: {
  page?: number;
  page_size?: number;
  search?: string;
  role?: string;
  is_active?: boolean;
}) {
  return useQuery<UserListResponse, ApiError>({
    queryKey: adminKeys.users(params),
    queryFn: () => getUsers(params),
  });
}

export function useUserDetail(
  userId: string | null,
  params?: { page?: number; page_size?: number },
) {
  return useQuery<UserDetailResponse, ApiError>({
    queryKey: adminKeys.userDetail(userId ?? "", params ?? {}),
    queryFn: () => getUserDetail(userId!, params),
    enabled: !!userId,
  });
}

export function useUpdateUserStatus() {
  const qc = useQueryClient();
  return useMutation<
    UpdateUserStatusResponse,
    ApiError,
    { userId: string; isActive: boolean }
  >({
    mutationFn: ({ userId, isActive }) =>
      updateUserStatus(userId, isActive),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminKeys.all });
    },
  });
}

// ---------------------------------------------------------------------------
// Interviews
// ---------------------------------------------------------------------------

export function useInterviews(params: {
  page?: number;
  page_size?: number;
  status?: string;
  interview_type?: string;
  search?: string;
}) {
  return useQuery<InterviewListResponse, ApiError>({
    queryKey: adminKeys.interviews(params),
    queryFn: () => getInterviews(params),
  });
}

export function useInterviewDetail(interviewId: string | null) {
  return useQuery<InterviewDetailResponse, ApiError>({
    queryKey: adminKeys.interviewDetail(interviewId ?? ""),
    queryFn: () => getInterviewDetail(interviewId!),
    enabled: !!interviewId,
  });
}

export function useAssignInterview() {
  const qc = useQueryClient();
  return useMutation<
    AssignInterviewResponse,
    ApiError,
    AssignInterviewRequest
  >({
    mutationFn: assignInterview,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminKeys.all });
    },
  });
}

export function useCancelInterview() {
  const qc = useQueryClient();
  return useMutation<InterviewDetailResponse, ApiError, string>({
    mutationFn: cancelInterview,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminKeys.all });
    },
  });
}

export function useRescheduleInterview() {
  const qc = useQueryClient();
  return useMutation<
    RescheduleInterviewResponse,
    ApiError,
    { interviewId: string } & RescheduleInterviewRequest
  >({
    mutationFn: ({ interviewId, ...body }) =>
      rescheduleInterview(interviewId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminKeys.all });
      qc.invalidateQueries({ queryKey: ["candidate"] });
      qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

// ---------------------------------------------------------------------------
// Evaluations
// ---------------------------------------------------------------------------

export function useEvaluations(params: {
  page?: number;
  page_size?: number;
  review_state?: string;
}) {
  return useQuery<EvaluationListResponse, ApiError>({
    queryKey: adminKeys.evaluations(params),
    queryFn: () => getEvaluations(params),
  });
}

export function useEvaluationDetail(sessionId: string | null) {
  return useQuery<EvaluationDetailResponse, ApiError>({
    queryKey: adminKeys.evaluationDetail(sessionId ?? ""),
    queryFn: () => getEvaluationDetail(sessionId!),
    enabled: !!sessionId,
  });
}

export function useSubmitDecision() {
  const qc = useQueryClient();
  return useMutation<
    SubmitDecisionResponse,
    ApiError,
    { sessionId: string; admin_decision: string; admin_feedback?: string | null }
  >({
    mutationFn: ({ sessionId, ...body }) =>
      submitDecision(sessionId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminKeys.all });
    },
  });
}

// ---------------------------------------------------------------------------
// Job Roles
// ---------------------------------------------------------------------------

export function useJobRoles() {
  return useQuery<JobRoleItem[], ApiError>({
    queryKey: adminKeys.jobRoles(),
    queryFn: getJobRoles,
  });
}
