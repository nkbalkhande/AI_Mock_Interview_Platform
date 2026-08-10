import { apiClient } from "@/lib/api-client";

import type {
  AssignedResultListResponse,
  DashboardResponse,
  PracticeResultListResponse,
  RecentResultsResponse,
  UpcomingInterviewDetail,
  UpcomingInterviewsResponse,
} from "./types";

/** GET /candidate/dashboard — profile summary + stat tile counts. */
export async function getDashboard(): Promise<DashboardResponse> {
  const { data } = await apiClient.get<DashboardResponse>(
    "/candidate/dashboard",
  );
  return data;
}

/** GET /candidate/upcoming-interviews — assigned interviews soonest first. */
export async function getUpcomingInterviews(
  limit = 20,
): Promise<UpcomingInterviewsResponse> {
  const { data } = await apiClient.get<UpcomingInterviewsResponse>(
    "/candidate/upcoming-interviews",
    { params: { limit } },
  );
  return data;
}

/** GET /candidate/upcoming-interviews/:id — single interview full detail. */
export async function getUpcomingInterviewDetail(
  interviewId: string,
): Promise<UpcomingInterviewDetail> {
  const { data } = await apiClient.get<UpcomingInterviewDetail>(
    `/candidate/upcoming-interviews/${interviewId}`,
  );
  return data;
}

/** GET /candidate/recent-results — split practice + assigned summaries. */
export async function getRecentResults(
  limitPerType = 5,
): Promise<RecentResultsResponse> {
  const { data } = await apiClient.get<RecentResultsResponse>(
    "/candidate/recent-results",
    { params: { limit_per_type: limitPerType } },
  );
  return data;
}

/** GET /candidate/results/practice — paginated practice results. */
export async function getPracticeResults(
  page = 1,
  pageSize = 20,
): Promise<PracticeResultListResponse> {
  const { data } = await apiClient.get<PracticeResultListResponse>(
    "/candidate/results/practice",
    { params: { page, page_size: pageSize } },
  );
  return data;
}

/** GET /candidate/results/assigned — paginated assigned results. */
export async function getAssignedResults(
  page = 1,
  pageSize = 20,
): Promise<AssignedResultListResponse> {
  const { data } = await apiClient.get<AssignedResultListResponse>(
    "/candidate/results/assigned",
    { params: { page, page_size: pageSize } },
  );
  return data;
}
