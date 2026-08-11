"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, ArrowRight, Loader2, Send } from "lucide-react";

import { AnswerBox } from "@/components/interview/answer-box";
import {
  CodingEditor,
  type SupportedLanguage,
} from "@/components/interview/coding-editor";
import { InterviewHeader } from "@/components/interview/interview-header";
import { InterviewProgress } from "@/components/interview/interview-progress";
import { InterviewTimer } from "@/components/interview/interview-timer";
import { QuestionCard } from "@/components/interview/question-card";
import { InterviewerVoice, MicInput } from "@/components/interview/voice-controls";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useSessionState,
  useSubmitAnswer,
  useSubmitCoding,
  useSubmitInterview,
} from "@/features/interviews/hooks";
import { useMicRecorder, useTextToSpeech } from "@/features/voice/hooks";
import { ROUTES } from "@/lib/constants";

/**
 * Interview player.
 *
 * The candidate lands here after starting a JD-based practice interview.
 * Behavior:
 *
 * - On mount, the session state is fetched (refresh-safe). If the session
 *   has already been submitted, we redirect straight to the result page.
 * - Text and coding answers use different UI + endpoints; the response of
 *   either mutation gives us the *next* question or a "done" signal.
 * - After the final question is answered, the CTA switches to "Submit
 *   Interview". Submit schedules background evaluation server-side and
 *   redirects to the results page (which polls until it becomes ready).
 * - Timer is client-side UX only (see plan trade-offs).
 */
export default function InterviewSessionPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params?.sessionId ?? null;
  const router = useRouter();

  const { data, isLoading, isError, error, refetch } = useSessionState(
    sessionId,
    { refetch: false },
  );

  // Auto-redirect once the server considers the session finished.
  useEffect(() => {
    if (!data || !sessionId) return;
    if (
      data.session_status === "SUBMITTED" ||
      data.session_status === "EVALUATING" ||
      data.session_status === "EVALUATED" ||
      data.session_status === "COMPLETED"
    ) {
      router.replace(ROUTES.candidate.practiceResult(sessionId));
    }
  }, [data, sessionId, router]);

  if (!sessionId) {
    return <PlayerErrorState message="Missing session id in the URL." />;
  }

  if (isLoading || !data) {
    return <PlayerLoadingState />;
  }

  if (isError) {
    return (
      <PlayerErrorState
        message={error?.message ?? "Could not load this session."}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <PlayerBody
      sessionId={sessionId}
      data={data}
    />
  );
}

interface PlayerBodyProps {
  sessionId: string;
  data: ReturnType<typeof useSessionState>["data"] & object;
}

function PlayerBody({ sessionId, data }: PlayerBodyProps) {
  const router = useRouter();
  const question = data.current_question;
  const [textAnswer, setTextAnswer] = useState<string>(
    question?.existing_answer ?? "",
  );
  const [code, setCode] = useState<string>(question?.existing_answer ?? "");
  const [language, setLanguage] = useState<SupportedLanguage>("python");
  const [startedAtQuestion, setStartedAtQuestion] = useState<number>(
    () => Date.now(),
  );

  const isCoding = question?.question_type === "CODING";

  const submitAnswer = useSubmitAnswer(sessionId);
  const submitCoding = useSubmitCoding(sessionId);
  const submitInterview = useSubmitInterview(sessionId);
  const tts = useTextToSpeech();
  const mic = useMicRecorder();

  // Whenever the current question changes (new question arrives), reset
  // local input state and question-timer.
  useEffect(() => {
    setTextAnswer(question?.existing_answer ?? "");
    setCode(question?.existing_answer ?? "");
    setStartedAtQuestion(Date.now());
  }, [question?.id, question?.existing_answer]);

  // Auto-speak every non-coding question as the interviewer voice.
  const lastSpokenQuestionId = useRef<string | null>(null);
  useEffect(() => {
    if (question && !isCoding && question.id !== lastSpokenQuestionId.current) {
      lastSpokenQuestionId.current = question.id;
      tts.speak(question.question_text);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [question?.id]);

  // When STT transcript arrives, append to the answer box.
  useEffect(() => {
    if (mic.transcript) {
      setTextAnswer((prev) =>
        prev ? `${prev}\n${mic.transcript}` : mic.transcript!,
      );
    }
  }, [mic.transcript]);
  const isBusy =
    submitAnswer.isPending ||
    submitCoding.isPending ||
    submitInterview.isPending;

  const currentInput = isCoding ? code : textAnswer;
  const canSubmitAnswer = !isBusy && currentInput.trim().length > 0;
  const mutationError = useMemo(() => {
    const err =
      submitAnswer.error ??
      submitCoding.error ??
      submitInterview.error ??
      null;
    return err?.message ?? null;
  }, [submitAnswer.error, submitCoding.error, submitInterview.error]);

  const handleAnswerSubmit = useCallback(async () => {
    if (!question || !canSubmitAnswer) return;
    const responseTime = Math.max(
      0,
      Math.floor((Date.now() - startedAtQuestion) / 1000),
    );
    if (isCoding) {
      await submitCoding.mutateAsync({
        question_id: question.id,
        code,
        language,
      });
    } else {
      await submitAnswer.mutateAsync({
        question_id: question.id,
        answer_text: textAnswer,
        response_time_seconds: responseTime,
      });
    }
  }, [
    question,
    canSubmitAnswer,
    isCoding,
    submitAnswer,
    submitCoding,
    code,
    language,
    textAnswer,
    startedAtQuestion,
  ]);

  const handleInterviewSubmit = useCallback(async () => {
    const result = await submitInterview.mutateAsync();
    router.replace(ROUTES.candidate.practiceResult(result.session_id));
  }, [submitInterview, router]);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <InterviewHeader interview={data.interview} />

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <InterviewProgress
          currentNumber={data.current_question_number || 1}
          totalQuestions={data.total_questions}
          answeredCount={data.answered_count}
          className="flex-1"
        />
        <InterviewTimer
          durationMinutes={data.interview.duration_minutes}
          startedAt={data.interview.started_at}
        />
      </div>

      {question ? (
        <>
          <QuestionCard question={question} />
          {!isCoding ? (
            <InterviewerVoice
              isTtsPlaying={tts.isPlaying}
              hasError={tts.hasError}
              onReplay={() => tts.speak(question.question_text)}
              onStop={tts.stop}
              disabled={isBusy || mic.isRecording}
            />
          ) : null}
        </>
      ) : (
        <Card>
          <CardContent className="p-6 text-sm text-muted-foreground">
            All questions have been answered. Submit the interview to receive
            your evaluation.
          </CardContent>
        </Card>
      )}

      {question ? (
        isCoding ? (
          <CodingEditor
            value={code}
            onValueChange={setCode}
            language={language}
            onLanguageChange={setLanguage}
            disabled={isBusy}
          />
        ) : (
          <div className="flex flex-col gap-3">
            <MicInput
              isRecording={mic.isRecording}
              isTranscribing={mic.isTranscribing}
              onStartRecording={mic.startRecording}
              onStopRecording={mic.stopRecording}
              error={mic.error}
              disabled={isBusy || tts.isPlaying}
            />
            <AnswerBox
              value={textAnswer}
              onValueChange={setTextAnswer}
              disabled={isBusy}
            />
          </div>
        )
      ) : null}

      {mutationError ? (
        <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-medium">Something went wrong.</p>
            <p className="text-destructive/80">{mutationError}</p>
          </div>
        </div>
      ) : null}

      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end">
        {question ? (
          <Button
            variant="default"
            onClick={handleAnswerSubmit}
            disabled={!canSubmitAnswer}
            aria-busy={submitAnswer.isPending || submitCoding.isPending}
          >
            {submitAnswer.isPending || submitCoding.isPending ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                Saving…
              </>
            ) : data.is_last_question ? (
              <>
                Save Final Answer
                <ArrowRight className="ml-1 h-4 w-4" />
              </>
            ) : (
              <>
                Save & Next Question
                <ArrowRight className="ml-1 h-4 w-4" />
              </>
            )}
          </Button>
        ) : null}

        {data.can_submit || !question ? (
          <Button
            variant="destructive"
            onClick={handleInterviewSubmit}
            disabled={submitInterview.isPending}
            aria-busy={submitInterview.isPending}
          >
            {submitInterview.isPending ? (
              <>
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                Submitting…
              </>
            ) : (
              <>
                <Send className="mr-1 h-4 w-4" />
                Submit Interview
              </>
            )}
          </Button>
        ) : null}
      </div>

      <p className="text-xs text-muted-foreground">
        Your answers are saved as you submit each question. It's safe to
        refresh — you'll come back to where you left off.
      </p>
    </div>
  );
}

// ---------- state helpers ----------

function PlayerLoadingState() {
  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="h-6 w-60" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-56 w-full" />
    </div>
  );
}

function PlayerErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <div className="flex items-start gap-3 rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
        <div className="flex flex-1 flex-col gap-2">
          <p className="font-medium">Could not load the interview.</p>
          <p className="text-destructive/80">{message}</p>
          {onRetry ? (
            <Button
              size="sm"
              variant="outline"
              onClick={onRetry}
              className="w-fit"
            >
              Try again
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}