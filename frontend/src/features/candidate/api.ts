import { apiClient } from "@/lib/api-client";

import type {
  AssignedResultDetail,
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

/** GET /candidate/results/assigned/:sessionId — single assigned result. */
export async function getAssignedResultDetail(
  sessionId: string,
): Promise<AssignedResultDetail> {
  const { data } = await apiClient.get<AssignedResultDetail>(
    `/candidate/results/assigned/${sessionId}`,
  );
  return data;
}

/** GET /candidate/interviews/history — full interview history (paginated + filtered). */
export async function getInterviewHistory(
  page = 1,
  pageSize = 20,
  statusFilter?: string | null,
  typeFilter?: string | null,
): Promise<InterviewHistoryResponse> {
  const params: Record<string, unknown> = { page, page_size: pageSize };
  if (statusFilter) params.status_filter = statusFilter;
  if (typeFilter) params.type_filter = typeFilter;
  const { data } = await apiClient.get<InterviewHistoryResponse>(
    "/candidate/interviews/history",
    { params },
  );
  return data;
}

/** GET /candidate/profile — full candidate profile. */
export async function getProfile(): Promise<CandidateProfileResponse> {
  const { data } = await apiClient.get<CandidateProfileResponse>(
    "/candidate/profile",
  );
  return data;
}

/** PATCH /candidate/profile — update the current candidate profile. */
export async function updateProfile(
  payload: CandidateProfileUpdateRequest,
): Promise<CandidateProfileResponse> {
  const { data } = await apiClient.patch<CandidateProfileResponse>(
    "/candidate/profile",
    payload,
  );
  return data;
}

/** PUT /candidate/profile/photo — upload or replace the profile photo. */
export async function uploadProfilePhoto(
  file: File,
): Promise<CandidateProfileResponse> {
  const formData = new FormData();
  formData.append("photo", file);
  const { data } = await apiClient.put<CandidateProfileResponse>(
    "/candidate/profile/photo",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return data;
}
