import { apiClient } from "@/lib/api-client";

import type {
  AnswerSubmissionRequest,
  AnswerSubmissionResponse,
  CodingSubmissionRequest,
  JobRole,
  PracticeResultResponse,
  SessionStateResponse,
  StartPracticeInterviewRequest,
  StartPracticeInterviewResponse,
  StartRolePracticeInterviewRequest,
  SubmitInterviewResponse,
} from "./types";

/** POST /candidate/interviews/practice/jd-based — create interview + first Q. */
export async function startJdPractice(
  payload: StartPracticeInterviewRequest,
): Promise<StartPracticeInterviewResponse> {
  const { data } = await apiClient.post<StartPracticeInterviewResponse>(
    "/candidate/interviews/practice/jd-based",
    payload,
  );
  return data;
}

export async function getJobRoles(): Promise<JobRole[]> {
  const { data } = await apiClient.get<JobRole[]>(
    "/candidate/interviews/job-roles",
  );
  return data;
}

export async function startRolePractice(
  payload: StartRolePracticeInterviewRequest,
): Promise<StartPracticeInterviewResponse> {
  const { data } = await apiClient.post<StartPracticeInterviewResponse>(
    "/candidate/interviews/practice/role-based",
    payload,
  );
  return data;
}

/** GET /candidate/interviews/sessions/{id} — refresh-safe player state. */
export async function getSessionState(
  sessionId: string,
): Promise<SessionStateResponse> {
  const { data } = await apiClient.get<SessionStateResponse>(
    `/candidate/interviews/sessions/${sessionId}`,
  );
  return data;
}

/** POST /candidate/interviews/sessions/{id}/answers — text answer + next Q. */
export async function submitAnswer(
  sessionId: string,
  payload: AnswerSubmissionRequest,
): Promise<AnswerSubmissionResponse> {
  const { data } = await apiClient.post<AnswerSubmissionResponse>(
    `/candidate/interviews/sessions/${sessionId}/answers`,
    payload,
  );
  return data;
}

/** POST /candidate/interviews/sessions/{id}/coding-submissions — code + next Q. */
export async function submitCoding(
  sessionId: string,
  payload: CodingSubmissionRequest,
): Promise<AnswerSubmissionResponse> {
  const { data } = await apiClient.post<AnswerSubmissionResponse>(
    `/candidate/interviews/sessions/${sessionId}/coding-submissions`,
    payload,
  );
  return data;
}

/** POST /candidate/interviews/sessions/{id}/submit — close + schedule eval. */
export async function submitInterview(
  sessionId: string,
): Promise<SubmitInterviewResponse> {
  const { data } = await apiClient.post<SubmitInterviewResponse>(
    `/candidate/interviews/sessions/${sessionId}/submit`,
  );
  return data;
}

export async function getPracticeResult(
  sessionId: string,
): Promise<PracticeResultResponse> {
  const { data } = await apiClient.get<PracticeResultResponse>(
    `/candidate/interviews/sessions/${sessionId}/result`,
  );
  return data;
}
