"use client";

import { use, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  XCircle,
  AlertTriangle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useEvaluationDetail,
  useSubmitDecision,
} from "@/features/admin/hooks";
import { ROUTES } from "@/lib/constants";
import { formatDateTime, formatScore } from "@/lib/format";

function verdictIcon(verdict: string | null) {
  if (verdict === "CLEARED")
    return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
  if (verdict === "NOT_CLEARED")
    return <XCircle className="h-5 w-5 text-destructive" />;
  return <AlertTriangle className="h-5 w-5 text-amber-500" />;
}

export default function EvaluationDetailPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = use(params);
  const { data, isLoading } = useEvaluationDetail(sessionId);
  const submit = useSubmitDecision();
  const [decision, setDecision] = useState("");
  const [feedback, setFeedback] = useState("");
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit() {
    if (!decision) return;
    try {
      await submit.mutateAsync({
        sessionId,
        admin_decision: decision,
        admin_feedback: feedback || null,
      });
      setSubmitted(true);
    } catch {
      // error handled by mutation state
    }
  }

  if (isLoading) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center gap-4 py-20">
        <p className="text-muted-foreground">Evaluation not found.</p>
        <Button variant="outline" asChild>
          <Link href={ROUTES.admin.evaluations}>Back to Evaluations</Link>
        </Button>
      </div>
    );
  }

  const alreadyDecided = !!data.admin_decision;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link href={ROUTES.admin.evaluations}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Evaluation Review
            </h1>
            <p className="text-sm text-muted-foreground">
              {data.candidate_name} &middot; {data.role ?? "N/A"}
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link href={`${ROUTES.admin.interviews}/${data.interview_id}`}>
            View Interview
          </Link>
        </Button>
      </div>

      {/* AI Summary */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">AI Assessment</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              {verdictIcon(data.ai_verdict)}
              <div>
                <p className="text-lg font-semibold">
                  {data.ai_verdict?.replace(/_/g, " ") ?? "Pending"}
                </p>
                <p className="text-sm text-muted-foreground">
                  Score: {formatScore(data.ai_overall_score)}
                  {data.ai_confidence
                    ? ` · Confidence: ${(Number(data.ai_confidence) * 100).toFixed(0)}%`
                    : ""}
                </p>
              </div>
            </div>

            {data.ai_summary ? (
              <p className="text-sm text-muted-foreground">
                {data.ai_summary}
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Session Info</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <Row label="Interview">{data.interview_type}</Row>
            <Row label="Duration">{data.duration_minutes} min</Row>
            <Row label="Started">
              {formatDateTime(data.session_started_at)}
            </Row>
            <Row label="Ended">
              {formatDateTime(data.session_ended_at)}
            </Row>
            <Row label="Status">{data.session_status}</Row>
          </CardContent>
        </Card>
      </div>

      {data.skill_scores.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Skill Scores</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              {data.skill_scores.map((skill) => (
                <div
                  key={skill.skill_name}
                  className="rounded-md border border-border p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium">{skill.skill_name}</p>
                    <span className="font-mono text-sm">
                      {formatScore(skill.score)}
                      {skill.max_score != null && skill.max_score !== ""
                        ? ` / ${Number(skill.max_score).toFixed(1)}`
                        : ""}
                    </span>
                  </div>
                  {skill.evidence.length > 0 ? (
                    <ul className="mt-2 flex flex-col gap-1 text-xs text-muted-foreground">
                      {skill.evidence.map((ev, i) => (
                        <li key={i}>&bull; {ev}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* Strengths / Weaknesses / Improvement */}
      {(data.ai_strengths.length > 0 ||
        data.ai_weaknesses.length > 0 ||
        data.ai_improvement_areas.length > 0) ? (
        <div className="grid gap-6 md:grid-cols-3">
          {data.ai_strengths.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm text-emerald-600">
                  Strengths
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-1 text-sm">
                  {data.ai_strengths.map((s, i) => (
                    <li key={i} className="text-muted-foreground">
                      &bull; {s}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
          {data.ai_weaknesses.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm text-destructive">
                  Weaknesses
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-1 text-sm">
                  {data.ai_weaknesses.map((w, i) => (
                    <li key={i} className="text-muted-foreground">
                      &bull; {w}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
          {data.ai_improvement_areas.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm text-amber-600">
                  Areas for Improvement
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-1 text-sm">
                  {data.ai_improvement_areas.map((a, i) => (
                    <li key={i} className="text-muted-foreground">
                      &bull; {a}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
        </div>
      ) : null}

      {/* Per-question breakdown */}
      {data.questions.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Question-by-Question Review ({data.questions.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {data.questions.map((q, idx) => (
              <div key={idx}>
                {idx > 0 ? <Separator className="mb-4" /> : null}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">
                      Q{q.question_number}.
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {q.question_type}
                    </Badge>
                    {q.difficulty ? (
                      <Badge variant="secondary" className="text-xs">
                        {q.difficulty}
                      </Badge>
                    ) : null}
                    {q.overall_score ? (
                      <span className="ml-auto text-sm font-mono">
                        {formatScore(q.overall_score)}
                      </span>
                    ) : null}
                  </div>

                  <p className="text-sm font-medium">{q.question_text}</p>

                  {q.candidate_answer ? (
                    <div className="rounded-md bg-muted/50 p-3">
                      <p className="text-xs font-semibold text-muted-foreground mb-1">
                        Candidate Answer
                      </p>
                      <p className="whitespace-pre-wrap text-sm">
                        {q.candidate_answer}
                      </p>
                    </div>
                  ) : (
                    <p className="text-sm italic text-muted-foreground">
                      No answer provided.
                    </p>
                  )}

                  {q.expected_answer ? (
                    <div className="rounded-md border border-emerald-200 bg-emerald-50/50 p-3 dark:border-emerald-900 dark:bg-emerald-950/20">
                      <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 mb-1">
                        Expected Answer
                      </p>
                      <p className="whitespace-pre-wrap text-sm">
                        {q.expected_answer}
                      </p>
                    </div>
                  ) : null}

                  {q.feedback ? (
                    <p className="text-sm text-muted-foreground">
                      <span className="font-medium">Feedback:</span>{" "}
                      {q.feedback}
                    </p>
                  ) : null}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {/* Admin Decision */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Admin Decision</CardTitle>
        </CardHeader>
        <CardContent>
          {submitted ? (
            <div className="flex items-center gap-3 py-4">
              <CheckCircle2 className="h-8 w-8 text-emerald-500" />
              <p className="text-lg font-semibold">Decision submitted!</p>
            </div>
          ) : alreadyDecided ? (
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Decision:</span>
                <Badge
                  variant={
                    data.admin_decision === "CLEARED"
                      ? "default"
                      : data.admin_decision === "NOT_CLEARED"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  {data.admin_decision?.replace(/_/g, " ")}
                </Badge>
              </div>
              {data.admin_feedback ? (
                <p className="text-sm text-muted-foreground">
                  {data.admin_feedback}
                </p>
              ) : null}
              <p className="text-xs text-muted-foreground">
                Decided by {data.decided_by_name ?? "—"} on{" "}
                {formatDateTime(data.decided_at)}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div>
                <Label>Your Decision</Label>
                <div className="mt-2 flex flex-wrap gap-2">
                  {[
                    { value: "CLEARED", label: "Cleared", color: "default" as const },
                    {
                      value: "NOT_CLEARED",
                      label: "Not Cleared",
                      color: "destructive" as const,
                    },
                    {
                      value: "NEEDS_FURTHER_REVIEW",
                      label: "Needs Further Review",
                      color: "secondary" as const,
                    },
                  ].map((opt) => (
                    <Button
                      key={opt.value}
                      type="button"
                      variant={
                        decision === opt.value ? opt.color : "outline"
                      }
                      size="sm"
                      onClick={() => setDecision(opt.value)}
                    >
                      {opt.label}
                    </Button>
                  ))}
                </div>
              </div>

              <div>
                <Label htmlFor="admin_feedback">
                  Feedback for Candidate (optional)
                </Label>
                <textarea
                  id="admin_feedback"
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  rows={4}
                  placeholder="Provide feedback visible to the candidate..."
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </div>

              {submit.isError ? (
                <p className="text-sm text-destructive">
                  {(submit.error as { message?: string })?.message ??
                    "Failed to submit decision."}
                </p>
              ) : null}

              <Button
                onClick={handleSubmit}
                disabled={!decision || submit.isPending}
              >
                {submit.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                Submit Decision
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2">
      <span className="w-24 shrink-0 font-medium text-muted-foreground">
        {label}
      </span>
      <span className="text-foreground">{children}</span>
    </div>
  );
}
