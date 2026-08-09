/**
 * DTOs mirroring the backend candidate interview API
 * (``/api/v1/candidate/interviews/*``). Snake_case matches the Pydantic
 * response shape so components consume the wire format directly.
 */

export type QuestionType =
  | "TECHNICAL"
  | "PROJECT"
  | "BEHAVIORAL"
  | "CODING"
  | "SYSTEM_DESIGN"
  | "FOLLOW_UP";

export type QuestionDifficulty = "EASY" | "MEDIUM" | "HARD";

export type SessionStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "PAUSED"
  | "SUBMITTED"
  | "EVALUATING"
  | "EVALUATED"
  | "COMPLETED"
  | "ABANDONED";

export interface InterviewSummary {
  id: string;
  interview_type: "PRACTICE" | "ASSIGNED";
  practice_type: "JD_BASED" | "ROLE_BASED" | null;
  role_name: string | null;
  duration_minutes: number;
  status: string;
  started_at: string | null;
}

export interface CurrentQuestion {
  id: string;
  question_number: number;
  question_text: string;
  question_type: QuestionType;
  difficulty: QuestionDifficulty | null;
  topic: string | null;
  skill: string | null;
  /** Populated on refresh after a submitted answer so the box isn't blank. */
  existing_answer: string | null;
}

export interface StartPracticeInterviewRequest {
  job_description: string;
  /**
   * Requested interview length in minutes. Backend clamps to
   * ``[15, 90]`` (see ``StartPracticeInterviewRequest`` on the FastAPI side)
   * and derives the target question count from it.
   */
  duration_minutes?: number;
}

export interface StartPracticeInterviewResponse {
  interview: InterviewSummary;
  session_id: string;
  total_questions: number;
  current_question_number: number;
  current_question: CurrentQuestion;
}

export interface JobRole {
  id: string;
  name: string;
  description: string | null;
  requirements: string[];
  skills: string[];
  experience_min: number | null;
  experience_max: number | null;
}

export type StartRolePracticeInterviewRequest =
  | {
      job_role_id: string;
      duration_minutes: number;
    }
  | {
      custom_role_name: string;
      custom_requirements: string[];
      custom_skills: string[];
      duration_minutes: number;
    };

export interface SessionStateResponse {
  interview: InterviewSummary;
  session_id: string;
  session_status: SessionStatus;
  total_questions: number;
  answered_count: number;
  current_question_number: number;
  current_question: CurrentQuestion | null;
  is_last_question: boolean;
  can_submit: boolean;
  timed_out: boolean;
}

export interface AnswerSubmissionRequest {
  question_id: string;
  answer_text: string;
  response_time_seconds?: number;
}

export interface CodingSubmissionRequest {
  question_id: string;
  code: string;
  language: string;
}

export interface AnswerSubmissionResponse {
  next_question: CurrentQuestion | null;
  is_last_question: boolean;
  total_questions: number;
  answered_count: number;
}

export interface SubmitInterviewResponse {
  session_id: string;
  interview_id: string;
  status: string;
  evaluation_status: "pending" | "ready";
}

export interface PracticeSkillScore {
  skill_name: string;
  score: number;
  max_score: number;
  strength: string | null;
  improvement_area: string | null;
  evidence: string[];
}

export interface PracticeResultResponse {
  session_id: string;
  status: "pending" | "retryable" | "completed";
  practice_type: "JD_BASED" | "ROLE_BASED";
  role_name: string | null;
  overall_score: number | null;
  technical_score: number | null;
  communication_score: number | null;
  reasoning_score: number | null;
  project_knowledge_score: number | null;
  ai_verdict: string | null;
  confidence: number | null;
  summary: string | null;
  strengths: string[];
  weaknesses: string[];
  improvement_areas: string[];
  skill_scores: PracticeSkillScore[];
}
