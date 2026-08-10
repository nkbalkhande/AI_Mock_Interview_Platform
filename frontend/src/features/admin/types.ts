/**
 * DTOs mirroring the backend admin API (`/api/v1/admin/*`).
 *
 * Snake_case fields match FastAPI's Pydantic response shape.
 */

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export interface AdminDashboardStats {
  total_candidates: number;
  total_interviews: number;
  pending_evaluations: number;
  completed_interviews: number;
}

export interface RecentActivityItem {
  id: string;
  event_type: string;
  description: string;
  actor_name: string | null;
  created_at: string;
}

export interface AdminDashboardResponse {
  stats: AdminDashboardStats;
  recent_activity: RecentActivityItem[];
}

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export interface UserListItem {
  id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  email_verified: boolean;
  roles: string[];
  current_organization: string | null;
  current_designation: string | null;
  years_of_experience: string | null;
  created_at: string;
  last_login_at: string | null;
}

export interface UserListResponse {
  items: UserListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserInterviewSummary {
  interview_id: string;
  interview_type: string;
  role: string | null;
  status: string;
  scheduled_at: string | null;
  created_at: string;
}

export interface UserDetailResponse {
  id: string;
  full_name: string;
  email: string;
  is_active: boolean;
  email_verified: boolean;
  roles: string[];
  current_organization: string | null;
  current_designation: string | null;
  years_of_experience: string | null;
  phone_number: string | null;
  bio: string | null;
  profile_photo_path: string | null;
  created_at: string;
  last_login_at: string | null;
  total_interviews: number;
  interviews: UserInterviewSummary[];
}

export interface UpdateUserStatusResponse {
  id: string;
  is_active: boolean;
}

// ---------------------------------------------------------------------------
// Interviews
// ---------------------------------------------------------------------------

export interface InterviewListItem {
  id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  interview_type: string;
  practice_type: string | null;
  role: string | null;
  status: string;
  scheduled_at: string | null;
  duration_minutes: number;
  assigned_by_name: string | null;
  created_at: string;
}

export interface InterviewListResponse {
  items: InterviewListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface InterviewDetailResponse {
  id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  interview_type: string;
  practice_type: string | null;
  role: string | null;
  job_description: string | null;
  role_requirements: string | null;
  required_experience_min: string | null;
  required_experience_max: string | null;
  status: string;
  scheduled_at: string | null;
  timezone: string | null;
  duration_minutes: number;
  access_start_at: string | null;
  access_end_at: string | null;
  instructions: string | null;
  assigned_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface AssignInterviewRequest {
  candidate_id: string;
  job_role_id?: string | null;
  role_name: string;
  job_description: string;
  role_requirements?: string | null;
  required_experience_min?: number | null;
  required_experience_max?: number | null;
  scheduled_at: string;
  timezone?: string;
  duration_minutes?: number;
  instructions?: string | null;
}

export interface AssignInterviewResponse {
  id: string;
  status: string;
  candidate_name: string;
  role: string | null;
  scheduled_at: string | null;
  message: string;
}

// ---------------------------------------------------------------------------
// Evaluations
// ---------------------------------------------------------------------------

export interface EvaluationListItem {
  session_id: string;
  interview_id: string;
  candidate_name: string;
  candidate_email: string;
  role: string | null;
  interview_type: string;
  ai_overall_score: string | null;
  ai_verdict: string | null;
  status: string;
  submitted_at: string | null;
}

export interface EvaluationListResponse {
  items: EvaluationListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface QuestionEvaluationDetail {
  question_number: number;
  question_text: string;
  question_type: string;
  difficulty: string | null;
  candidate_answer: string | null;
  expected_answer: string | null;
  correctness_score: string | null;
  technical_score: string | null;
  communication_score: string | null;
  reasoning_score: string | null;
  overall_score: string | null;
  feedback: string | null;
  strengths: string[];
  weaknesses: string[];
}

export interface EvaluationDetailResponse {
  session_id: string;
  interview_id: string;
  candidate_name: string;
  candidate_email: string;
  role: string | null;
  interview_type: string;
  practice_type: string | null;
  duration_minutes: number;
  scheduled_at: string | null;
  ai_overall_score: string | null;
  ai_verdict: string | null;
  ai_confidence: string | null;
  ai_summary: string | null;
  ai_strengths: string[];
  ai_weaknesses: string[];
  ai_improvement_areas: string[];
  admin_decision: string | null;
  admin_feedback: string | null;
  decided_by_name: string | null;
  decided_at: string | null;
  questions: QuestionEvaluationDetail[];
  session_status: string;
  session_started_at: string | null;
  session_ended_at: string | null;
}

export interface SubmitDecisionResponse {
  session_id: string;
  admin_decision: string;
  decided_at: string;
  message: string;
}

// ---------------------------------------------------------------------------
// Job Roles
// ---------------------------------------------------------------------------

export interface JobRoleItem {
  id: string;
  name: string;
  description: string | null;
  requirements: string[];
  skills: string[];
  experience_min: string | null;
  experience_max: string | null;
  is_active: boolean;
}
