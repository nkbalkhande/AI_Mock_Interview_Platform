import { apiClient } from "@/lib/api-client";

import type {
  DashboardResponse,
  RecentResultsResponse,
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
