"use client";

import { useQuery } from "@tanstack/react-query";

import { getDashboard, getRecentResults, getUpcomingInterviews } from "./api";
import type {
  DashboardResponse,
  RecentResultsResponse,
  UpcomingInterviewsResponse,
} from "./types";
import type { ApiError } from "@/features/auth/types";

/** Shared query-key namespace so cache invalidation stays greppable. */
export const candidateKeys = {
  all: ["candidate"] as const,
  dashboard: () => [...candidateKeys.all, "dashboard"] as const,
  upcoming: (limit: number) =>
    [...candidateKeys.all, "upcoming", limit] as const,
  recentResults: (limitPerType: number) =>
    [...candidateKeys.all, "recent-results", limitPerType] as const,
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
    // Access-window transitions matter — poke the server every minute so
    // "Scheduled" flips to "Join Interview" without a manual refresh.
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
