"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import type { ApiError } from "@/features/auth/types";

import {
  getJobRoles,
  getPracticeResult,
  getSessionState,
  startAssignedInterview,
  startJdPractice,
  startRolePractice,
  submitAnswer,
  submitCoding,
  submitInterview,
} from "./api";
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

export const interviewKeys = {
  all: ["interviews"] as const,
  session: (sessionId: string) =>
    [...interviewKeys.all, "session", sessionId] as const,
  roles: () => [...interviewKeys.all, "job-roles"] as const,
  result: (sessionId: string) =>
    [...interviewKeys.all, "result", sessionId] as const,
};

export function useJobRoles() {
  return useQuery<JobRole[], ApiError>({
    queryKey: interviewKeys.roles(),
    queryFn: getJobRoles,
    staleTime: 5 * 60_000,
  });
}

export function usePracticeResult(sessionId: string) {
  return useQuery<PracticeResultResponse, ApiError>({
    queryKey: interviewKeys.result(sessionId),
    queryFn: () => getPracticeResult(sessionId),
    enabled: Boolean(sessionId),
    refetchInterval: (query) =>
      query.state.data?.status === "pending" ? 3_000 : false,
  });
}

/**
 * Poll a session's state.
 *
 * Polling defaults to 5s while the session is still in progress or being
 * evaluated so the UI catches the async evaluation transition without a
 * manual refresh. Once the session is ``EVALUATED`` / ``COMPLETED`` the
 * caller can turn polling off by unmounting or passing ``refetch: false``.
 */
export function useSessionState(
  sessionId: string | null,
  options?: { refetch?: boolean; intervalMs?: number },
) {
  const enabled = Boolean(sessionId);
  const shouldRefetch = options?.refetch ?? true;
  const interval = options?.intervalMs ?? 5_000;
  return useQuery<SessionStateResponse, ApiError>({
    queryKey: sessionId
      ? interviewKeys.session(sessionId)
      : [...interviewKeys.all, "session", "none"],
    queryFn: () => getSessionState(sessionId as string),
    enabled,
    refetchInterval: shouldRefetch ? interval : false,
    // Stale time 0 so a refetch after a mutation always hits the server.
    staleTime: 0,
  });
}

export function useStartJdPractice() {
  const queryClient = useQueryClient();
  return useMutation<
    StartPracticeInterviewResponse,
    ApiError,
    StartPracticeInterviewRequest
  >({
    mutationFn: startJdPractice,
    onSuccess: (data) => {
      // Seed the session-state cache with the freshly returned payload —
      // saves a network round-trip on the very first player render.
      queryClient.setQueryData<SessionStateResponse>(
        interviewKeys.session(data.session_id),
        {
          interview: data.interview,
          session_id: data.session_id,
          session_status: "IN_PROGRESS",
          total_questions: data.total_questions,
          answered_count: 0,
          current_question_number: data.current_question_number,
          current_question: data.current_question,
          is_last_question:
            data.current_question_number === data.total_questions,
          can_submit: false,
          timed_out: false,
        },
      );
    },
  });
}

export function useStartRolePractice() {
  const queryClient = useQueryClient();
  return useMutation<
    StartPracticeInterviewResponse,
    ApiError,
    StartRolePracticeInterviewRequest
  >({
    mutationFn: startRolePractice,
    onSuccess: (data) => {
      queryClient.setQueryData<SessionStateResponse>(
        interviewKeys.session(data.session_id),
        {
          interview: data.interview,
          session_id: data.session_id,
          session_status: "IN_PROGRESS",
          total_questions: data.total_questions,
          answered_count: 0,
          current_question_number: data.current_question_number,
          current_question: data.current_question,
          is_last_question:
            data.current_question_number === data.total_questions,
          can_submit: false,
          timed_out: false,
        },
      );
    },
  });
}

export function useStartAssignedInterview() {
  return useMutation<StartPracticeInterviewResponse, ApiError, string>({
    mutationFn: startAssignedInterview,
  });
}

export function useSubmitAnswer(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    AnswerSubmissionResponse,
    ApiError,
    AnswerSubmissionRequest
  >({
    mutationFn: (payload) => submitAnswer(sessionId, payload),
    onSuccess: () => {
      // Refetch state so the player picks up the new question / progress.
      queryClient.invalidateQueries({
        queryKey: interviewKeys.session(sessionId),
      });
    },
  });
}

export function useSubmitCoding(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation<
    AnswerSubmissionResponse,
    ApiError,
    CodingSubmissionRequest
  >({
    mutationFn: (payload) => submitCoding(sessionId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: interviewKeys.session(sessionId),
      });
    },
  });
}

export function useSubmitInterview(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation<SubmitInterviewResponse, ApiError, void>({
    mutationFn: () => submitInterview(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: interviewKeys.session(sessionId),
      });
      queryClient.invalidateQueries({
        queryKey: interviewKeys.result(sessionId),
      });
    },
  });
}
