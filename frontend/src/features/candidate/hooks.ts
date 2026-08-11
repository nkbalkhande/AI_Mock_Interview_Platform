"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getAssignedResults,
  getDashboard,
  getInterviewHistory,
  getPracticeResults,
  getProfile,
  getRecentResults,
  getUpcomingInterviewDetail,
  getUpcomingInterviews,
  updateProfile,
  uploadProfilePhoto,
} from "./api";
import type {
  AssignedResultListResponse,
  CandidateProfileResponse,
  CandidateProfileUpdateRequest,
  DashboardResponse,
  InterviewHistoryResponse,
  PracticeResultListResponse,
  RecentResultsResponse,
  UpcomingInterviewDetail,
  UpcomingInterviewsResponse,
} from "./types";
import type { ApiError } from "@/features/auth/types";

/** Shared query-key namespace so cache invalidation stays greppable. */
export const candidateKeys = {
  all: ["candidate"] as const,
  dashboard: () => [...candidateKeys.all, "dashboard"] as const,
  profile: () => [...candidateKeys.all, "profile"] as const,
  upcoming: (limit: number) =>
    [...candidateKeys.all, "upcoming", limit] as const,
  upcomingDetail: (id: string) =>
    [...candidateKeys.all, "upcoming-detail", id] as const,
  recentResults: (limitPerType: number) =>
    [...candidateKeys.all, "recent-results", limitPerType] as const,
  practiceResults: (page: number, pageSize: number) =>
    [...candidateKeys.all, "practice-results", page, pageSize] as const,
  assignedResults: (page: number, pageSize: number) =>
    [...candidateKeys.all, "assigned-results", page, pageSize] as const,
  interviewHistory: (
    page: number,
    pageSize: number,
    statusFilter: string | null,
    typeFilter: string | null,
  ) =>
    [
      ...candidateKeys.all,
      "interview-history",
      page,
      pageSize,
      statusFilter,
      typeFilter,
    ] as const,
};

/** Dashboard overview (profile summary + stat tiles). */
export function useCandidateDashboard() {
  return useQuery<DashboardResponse, ApiError>({
    queryKey: candidateKeys.dashboard(),
    queryFn: getDashboard,
  });
}

/** Upcoming assigned interviews for the current candidate. */
export function useUpcomingInterviews(limit = 20) {
  return useQuery<UpcomingInterviewsResponse, ApiError>({
    queryKey: candidateKeys.upcoming(limit),
    queryFn: () => getUpcomingInterviews(limit),
    refetchInterval: 60_000,
  });
}

/** Full details for a single upcoming assigned interview. */
export function useUpcomingInterviewDetail(interviewId: string | null) {
  return useQuery<UpcomingInterviewDetail, ApiError>({
    queryKey: candidateKeys.upcomingDetail(interviewId ?? ""),
    queryFn: () => getUpcomingInterviewDetail(interviewId!),
    enabled: !!interviewId,
    refetchInterval: 60_000,
  });
}

/** Recent practice + assigned results. */
export function useRecentResults(limitPerType = 5) {
  return useQuery<RecentResultsResponse, ApiError>({
    queryKey: candidateKeys.recentResults(limitPerType),
    queryFn: () => getRecentResults(limitPerType),
  });
}

/** Paginated practice interview results. */
export function usePracticeResults(page = 1, pageSize = 20) {
  return useQuery<PracticeResultListResponse, ApiError>({
    queryKey: candidateKeys.practiceResults(page, pageSize),
    queryFn: () => getPracticeResults(page, pageSize),
  });
}

/** Full candidate profile for the profile settings page. */
export function useCandidateProfile() {
  return useQuery<CandidateProfileResponse, ApiError>({
    queryKey: candidateKeys.profile(),
    queryFn: getProfile,
  });
}

export function useUpdateCandidateProfile() {
  const queryClient = useQueryClient();

  return useMutation<CandidateProfileResponse, ApiError, CandidateProfileUpdateRequest>({
    mutationFn: updateProfile,
    onSuccess: (updated) => {
      queryClient.setQueryData(candidateKeys.profile(), updated);
      queryClient.invalidateQueries({ queryKey: candidateKeys.profile() });
    },
  });
}

export function useUploadProfilePhoto() {
  const queryClient = useQueryClient();

  return useMutation<CandidateProfileResponse, ApiError, File>({
    mutationFn: uploadProfilePhoto,
    onSuccess: (updated) => {
      queryClient.setQueryData(candidateKeys.profile(), updated);
      queryClient.invalidateQueries({ queryKey: candidateKeys.dashboard() });
      queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

/** Paginated assigned interview results. */
export function useAssignedResults(page = 1, pageSize = 20) {
  return useQuery<AssignedResultListResponse, ApiError>({
    queryKey: candidateKeys.assignedResults(page, pageSize),
    queryFn: () => getAssignedResults(page, pageSize),
  });
}

/** Full interview history with status/type filters. */
export function useInterviewHistory(
  page = 1,
  pageSize = 20,
  statusFilter: string | null = null,
  typeFilter: string | null = null,
) {
  return useQuery<InterviewHistoryResponse, ApiError>({
    queryKey: candidateKeys.interviewHistory(
      page,
      pageSize,
      statusFilter,
      typeFilter,
    ),
    queryFn: () =>
      getInterviewHistory(page, pageSize, statusFilter, typeFilter),
  });
}
