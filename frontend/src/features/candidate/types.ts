/**
 * DTOs mirroring the backend candidate API (``/api/v1/candidate/*``).
 *
 * Snake_case fields match FastAPI's Pydantic response shape (see
 * ``backend/app/api/v1/candidate/schemas.py``). We deliberately do NOT remap
 * to camelCase in this layer — components consume these directly so the wire
 * shape is the contract, keeping serializer bugs cheap to spot.
 */

export interface CandidateProfileSummary {
  id: string;
  full_name: string;
  email: string;
  current_designation: string | null;
  current_organization: string | null;
  /** Numeric decimal serialized as string by Pydantic (numeric(4,2)). */
  years_of_experience: string | null;
  profile_photo_path: string | null;
}

export interface CandidateProfileResponse {
  id: string;
  full_name: string;
  email: string;
  current_designation: string | null;
  current_organization: string | null;
  years_of_experience: string | null;
  phone_number: string | null;
  bio: string | null;
  profile_photo_path: string | null;
}

export interface CandidateProfileUpdateRequest {
  full_name: string;
  current_organization: string;
  current_designation: string;
  years_of_experience: number;
  phone_number?: string | null;
  bio?: string | null;
}

export interface DashboardStats {
  practice_interviews: number;
  upcoming_interviews: number;
  completed_interviews: number;
  /** Numeric on 0-10 scale, string-serialized. Null when no data yet. */
  average_practice_score: string | null;
}

export interface DashboardResponse {
  profile: CandidateProfileSummary;
  stats: DashboardStats;
}

/** Matches ``AccessState`` on the backend (services/interviews/access_window). */
export type AccessState = "PENDING" | "OPEN" | "CLOSED";

export interface UpcomingInterview {
  id: string;
  role: string | null;
  organization: string | null;
  job_description: string | null;
  required_experience_min: string | null;
  required_experience_max: string | null;
  scheduled_at: string | null;
  timezone: string | null;
  duration_minutes: number;
  status: string;
  access_state: AccessState;
  access_start_at: string | null;
  access_end_at: string | null;
}

export interface UpcomingInterviewDetail extends UpcomingInterview {
  instructions: string | null;
  assigned_by_name: string | null;
}

export interface UpcomingInterviewsResponse {
  items: UpcomingInterview[];
}

export interface PracticeResultSummary {
  interview_id: string;
  session_id: string | null;
  role: string | null;
  completed_at: string | null;
  overall_score: string | null;
  technical_score: string | null;
  communication_score: string | null;
  strengths: string[];
  weaknesses: string[];
}

export interface PracticeResultListItem {
  interview_id: string;
  session_id: string | null;
  practice_type: "JD_BASED" | "ROLE_BASED" | null;
  role: string | null;
  duration_minutes: number | null;
  completed_at: string | null;
  overall_score: string | null;
  technical_score: string | null;
  communication_score: string | null;
  reasoning_score: string | null;
  project_knowledge_score: string | null;
  ai_verdict: string | null;
  strengths: string[];
  weaknesses: string[];
}

export interface PracticeResultListResponse {
  items: PracticeResultListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AssignedResultSummary {
  interview_id: string;
  session_id: string | null;
  role: string | null;
  completed_at: string | null;
  ai_overall_score: string | null;
  ai_verdict: string | null;
  admin_decision: string | null;
  admin_feedback: string | null;
  result_published_at: string | null;
}

export interface AssignedResultListItem {
  interview_id: string;
  session_id: string | null;
  role: string | null;
  duration_minutes: number | null;
  completed_at: string | null;
  ai_overall_score: string | null;
  ai_verdict: string | null;
  admin_decision: string | null;
  admin_feedback: string | null;
  result_published_at: string | null;
}

export interface AssignedResultListResponse {
  items: AssignedResultListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface RecentResultsResponse {
  practice: PracticeResultSummary[];
  assigned: AssignedResultSummary[];
}

// ── Interview History ─────────────────────────────────────────────────

export interface InterviewHistoryItem {
  interview_id: string;
  session_id: string | null;
  interview_type: "PRACTICE" | "ASSIGNED";
  practice_type: "JD_BASED" | "ROLE_BASED" | null;
  role: string | null;
  display_status: string;
  interview_status: string;
  session_status: string | null;
  can_resume: boolean;
  started_at: string | null;
  last_activity_at: string | null;
  duration_minutes: number;
  overall_score: string | null;
  answered_count: number;
  total_questions: number;
}

export interface InterviewHistoryResponse {
  items: InterviewHistoryItem[];
  total: number;
  page: number;
  page_size: number;
}
