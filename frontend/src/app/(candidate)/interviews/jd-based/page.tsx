"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, Clock, FileText, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { useStartJdPractice } from "@/features/interviews/hooks";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

// Kept in lockstep with the backend limits in
// ``services.interviews.lifecycle_service`` — if either side moves, keep
// the numbers matched so the UX matches what actually validates server-side.
const JD_MIN_CHARS = 200;
const JD_MAX_CHARS = 20000;

interface DurationOption {
  minutes: number;
  label: string;
  description: string;
}

// Options mirror the backend's ``_compute_target_questions`` bands so the
// user's picked duration → expected question count description is honest.
const DURATION_OPTIONS: DurationOption[] = [
  { minutes: 15, label: "15 min", description: "~5 questions" },
  { minutes: 30, label: "30 min", description: "~7 questions" },
  { minutes: 45, label: "45 min", description: "~8 questions" },
  { minutes: 60, label: "60 min", description: "~9 questions" },
];

const DEFAULT_DURATION_MINUTES = 30;

export default function JdBasedInterviewPage() {
  const router = useRouter();
  const [jd, setJd] = useState("");
  const [durationMinutes, setDurationMinutes] = useState<number>(
    DEFAULT_DURATION_MINUTES,
  );
  const mutation = useStartJdPractice();

  const trimmedLength = useMemo(() => jd.trim().length, [jd]);
  const validationMessage = useMemo(() => {
    if (trimmedLength === 0) return null;
    if (trimmedLength < JD_MIN_CHARS) {
      return `Add ${JD_MIN_CHARS - trimmedLength} more characters — the AI needs enough detail to interview you well.`;
    }
    if (trimmedLength > JD_MAX_CHARS) {
      return `Job description is too long by ${trimmedLength - JD_MAX_CHARS} characters.`;
    }
    return null;
  }, [trimmedLength]);

  const isValid =
    trimmedLength >= JD_MIN_CHARS && trimmedLength <= JD_MAX_CHARS;

  const selectedOption = useMemo(
    () =>
      DURATION_OPTIONS.find((opt) => opt.minutes === durationMinutes) ??
      DURATION_OPTIONS[1],
    [durationMinutes],
  );

  async function handleStart() {
    if (!isValid) return;
    const result = await mutation.mutateAsync({
      job_description: jd,
      duration_minutes: durationMinutes,
    });
    router.push(ROUTES.candidate.interview(result.session_id));
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <Link
        href={ROUTES.candidate.dashboard}
        className="inline-flex w-fit items-center gap-1 text-sm text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to dashboard
      </Link>

      <header className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground">
            <FileText className="h-5 w-5" />
          </span>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            JD-Based Practice Interview
          </h1>
        </div>
        <p className="text-sm text-muted-foreground">
          Paste the full job description below and choose how long you want to
          practice. The AI will tailor questions to the role using your current
          resume and experience.
        </p>
      </header>

      <div className="grid gap-3 sm:grid-cols-3">
        <FeatureBadge
          title="Adaptive AI"
          description="Follow-ups adjust to your answers."
        />
        <FeatureBadge
          title="Duration-driven"
          description="Question count scales with your chosen length."
        />
        <FeatureBadge
          title="Uses your resume"
          description="Backed by the resume you already uploaded."
        />
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-1 pb-3">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <label
              htmlFor="duration-input"
              className="text-sm font-semibold text-foreground"
            >
              Interview length
            </label>
          </div>
          <p className="text-xs text-muted-foreground">
            Pick how long the interview should run. Shorter sessions focus on
            core topics; longer sessions add depth and coding.
          </p>
        </CardHeader>
        <CardContent
          className="pt-0"
          id="duration-input"
          role="radiogroup"
          aria-label="Interview length in minutes"
        >
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {DURATION_OPTIONS.map((opt) => {
              const selected = opt.minutes === durationMinutes;
              return (
                <button
                  key={opt.minutes}
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => setDurationMinutes(opt.minutes)}
                  disabled={mutation.isPending}
                  className={cn(
                    "flex flex-col items-start gap-0.5 rounded-lg border px-3 py-2 text-left transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    "disabled:cursor-not-allowed disabled:opacity-60",
                    selected
                      ? "border-primary bg-primary/5 text-foreground"
                      : "border-border bg-card hover:border-primary/40 hover:bg-accent/40",
                  )}
                >
                  <span className="text-sm font-semibold">{opt.label}</span>
                  <span className="text-xs text-muted-foreground">
                    {opt.description}
                  </span>
                </button>
              );
            })}
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Selected:{" "}
            <span className="font-medium text-foreground">
              {selectedOption.label}
            </span>{" "}
            · {selectedOption.description}. The AI decides the flow — expect
            introduction, technical depth, project questions, and a wrap-up.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-col gap-1 pb-3">
          <div className="flex items-center justify-between">
            <label
              htmlFor="jd-input"
              className="text-sm font-semibold text-foreground"
            >
              Job description
            </label>
            <span
              className={
                trimmedLength > JD_MAX_CHARS
                  ? "text-xs tabular-nums text-destructive"
                  : "text-xs tabular-nums text-muted-foreground"
              }
            >
              {trimmedLength.toLocaleString()} /{" "}
              {JD_MAX_CHARS.toLocaleString()} characters
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Minimum {JD_MIN_CHARS} characters. Include responsibilities,
            required skills, and any tech stack details for the best results.
          </p>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 pt-0">
          <textarea
            id="jd-input"
            className="min-h-[280px] w-full resize-y rounded-md border border-input bg-transparent p-3 font-mono text-sm leading-relaxed shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the complete job description here — role summary, responsibilities, required qualifications, and tech stack…"
            maxLength={JD_MAX_CHARS + 100}
            disabled={mutation.isPending}
            aria-invalid={validationMessage !== null && !mutation.isPending}
            aria-describedby={validationMessage ? "jd-validation" : undefined}
          />

          {validationMessage ? (
            <p
              id="jd-validation"
              className="text-xs text-amber-600 dark:text-amber-400"
            >
              {validationMessage}
            </p>
          ) : null}

          {mutation.isError ? (
            <p className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
              {mutation.error.message ??
                "Could not start the interview. Please try again."}
            </p>
          ) : null}

          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Button
              variant="ghost"
              onClick={() => setJd("")}
              disabled={mutation.isPending || jd.length === 0}
            >
              Clear
            </Button>
            <Button
              onClick={handleStart}
              disabled={!isValid || mutation.isPending}
              aria-busy={mutation.isPending}
            >
              {mutation.isPending ? "Generating first question…" : (
                <>
                  Start {selectedOption.label} Interview
                  <ArrowRight className="ml-1 h-4 w-4" />
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function FeatureBadge({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-card p-3">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
        <Sparkles className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
