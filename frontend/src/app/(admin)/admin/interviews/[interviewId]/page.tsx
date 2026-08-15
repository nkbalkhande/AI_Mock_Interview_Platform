"use client";

import { use, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  CalendarClock,
  ClipboardCheck,
  FileText,
  XCircle,
} from "lucide-react";

import { RescheduleInterviewDialog } from "@/components/admin/reschedule-interview-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCancelInterview,
  useInterviewDetail,
} from "@/features/admin/hooks";
import { ROUTES, storageFileUrl } from "@/lib/constants";
import { formatDateTime, formatDuration, formatScore } from "@/lib/format";

const NON_CANCELLABLE = new Set(["CANCELLED", "COMPLETED", "EXPIRED"]);
const EVALUATION_STATUSES = new Set([
  "AI_EVALUATED",
  "ADMIN_REVIEW",
  "COMPLETED",
  "SUBMITTED",
]);

export default function InterviewDetailPage({
  params,
}: {
  params: Promise<{ interviewId: string }>;
}) {
  const { interviewId } = use(params);
  const { data: iv, isLoading } = useInterviewDetail(interviewId);
  const cancel = useCancelInterview();
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!iv) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center gap-4 py-20">
        <p className="text-muted-foreground">Interview not found.</p>
        <Button variant="outline" asChild>
          <Link href={ROUTES.admin.interviews}>Back to Interviews</Link>
        </Button>
      </div>
    );
  }

  const badgeLabel = (iv.display_status ?? iv.status).replace(/_/g, " ");
  const canCancel = !NON_CANCELLABLE.has(iv.status);
  const canReview =
    !!iv.session_id && EVALUATION_STATUSES.has(iv.status);
  const resumeUrl = storageFileUrl(iv.resume_file_path);
  const hasScores = iv.overall_score != null;

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" asChild>
            <Link href={ROUTES.admin.interviews}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Interview Details
            </h1>
            <p className="text-sm text-muted-foreground">
              {iv.role ?? "N/A"} &middot; {iv.candidate_name}
            </p>
            {successMessage ? (
              <p className="mt-1 text-sm text-emerald-600 dark:text-emerald-400">
                {successMessage}
              </p>
            ) : null}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {iv.can_reschedule ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setRescheduleOpen(true)}
            >
              <CalendarClock className="mr-2 h-4 w-4" />
              Reschedule
            </Button>
          ) : null}
          {canCancel ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => cancel.mutate(iv.id)}
              disabled={cancel.isPending}
            >
              <XCircle className="mr-2 h-4 w-4" />
              Cancel Interview
            </Button>
          ) : null}
          {canReview ? (
            <Button variant="default" size="sm" asChild>
              <Link href={`${ROUTES.admin.evaluations}/${iv.session_id}`}>
                <ClipboardCheck className="mr-2 h-4 w-4" />
                Review Evaluation
              </Link>
            </Button>
          ) : null}
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Interview Info</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <Row label="Type">
              <Badge variant="outline">{iv.interview_type}</Badge>
              {iv.practice_type ? (
                <Badge variant="secondary" className="ml-1">
                  {iv.practice_type.replace("_", " ")}
                </Badge>
              ) : null}
            </Row>
            <Row label="Role">{iv.role ?? "—"}</Row>
            <Row label="Status">
              <Badge variant="outline">{badgeLabel}</Badge>
            </Row>
            <Row label="Duration">{formatDuration(iv.duration_minutes)}</Row>
            <Row label="Scheduled">{formatDateTime(iv.scheduled_at)}</Row>
            {iv.original_scheduled_at ? (
              <Row label="Original Schedule">
                {formatDateTime(iv.original_scheduled_at)}
              </Row>
            ) : null}
            {iv.rescheduled_at ? (
              <Row label="Rescheduled">
                {formatDateTime(iv.rescheduled_at)}
                {iv.reschedule_count > 0
                  ? ` · ${iv.reschedule_count} time${iv.reschedule_count === 1 ? "" : "s"}`
                  : ""}
              </Row>
            ) : null}
            {iv.rescheduled_by_name ? (
              <Row label="Rescheduled By">{iv.rescheduled_by_name}</Row>
            ) : null}
            {iv.reschedule_reason ? (
              <Row label="Reschedule Reason">{iv.reschedule_reason}</Row>
            ) : null}
            <Row label="Started">{formatDateTime(iv.started_at)}</Row>
            <Row label="Completed">{formatDateTime(iv.completed_at)}</Row>
            <Row label="Timezone">{iv.timezone ?? "—"}</Row>
            <Row label="Access Window">
              {iv.access_start_at && iv.access_end_at
                ? `${formatDateTime(iv.access_start_at)} — ${formatDateTime(iv.access_end_at)}`
                : "—"}
            </Row>
            <Row label="Assigned By">{iv.assigned_by_name ?? "—"}</Row>
            <Row label="Created">{formatDateTime(iv.created_at)}</Row>
            {iv.admin_decision ? (
              <Row label="Admin Decision">
                <Badge variant="secondary">
                  {iv.admin_decision.replace(/_/g, " ")}
                </Badge>
              </Row>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Candidate</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <Row label="Name">{iv.candidate_name}</Row>
            <Row label="Email">{iv.candidate_email}</Row>
            {iv.required_experience_min != null ||
            iv.required_experience_max != null ? (
              <Row label="Required Experience">
                {iv.required_experience_min ?? "0"}–
                {iv.required_experience_max ?? "N/A"} yrs
              </Row>
            ) : null}
            <div className="pt-2">
              <Button variant="outline" size="sm" asChild>
                <Link href={`${ROUTES.admin.users}/${iv.candidate_id}`}>
                  View Candidate
                </Link>
              </Button>
            </div>
            {resumeUrl ? (
              <div>
                <Button variant="outline" size="sm" asChild>
                  <a href={resumeUrl} target="_blank" rel="noopener noreferrer">
                    <FileText className="mr-2 h-4 w-4" />
                    {iv.resume_file_name ?? "View Resume"}
                  </a>
                </Button>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {hasScores ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <ScoreCard label="Overall" value={iv.overall_score} />
          <ScoreCard label="Technical" value={iv.technical_score} />
          <ScoreCard label="Communication" value={iv.communication_score} />
          <ScoreCard label="Reasoning" value={iv.reasoning_score} />
        </div>
      ) : null}

      {(iv.strengths.length > 0 || iv.weaknesses.length > 0) ? (
        <div className="grid gap-6 md:grid-cols-2">
          {iv.strengths.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm text-emerald-600">
                  Strengths
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-1 text-sm">
                  {iv.strengths.map((s, i) => (
                    <li key={i} className="text-muted-foreground">
                      &bull; {s}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
          {iv.weaknesses.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm text-destructive">
                  Weaknesses
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-1 text-sm">
                  {iv.weaknesses.map((w, i) => (
                    <li key={i} className="text-muted-foreground">
                      &bull; {w}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
        </div>
      ) : null}

      {iv.questions.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Questions ({iv.answered_count}/{iv.total_questions})
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {iv.questions.map((q, idx) => (
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
                    {q.overall_score != null ? (
                      <span className="ml-auto font-mono text-sm">
                        {formatScore(q.overall_score)}
                      </span>
                    ) : null}
                  </div>
                  <p className="text-sm font-medium">{q.question_text}</p>
                  {q.candidate_answer ? (
                    <div className="rounded-md bg-muted/50 p-3">
                      <p className="mb-1 text-xs font-semibold text-muted-foreground">
                        Answer
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

      {iv.job_description ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Job Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">
              {iv.job_description}
            </p>
          </CardContent>
        </Card>
      ) : null}

      {iv.instructions ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Instructions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">
              {iv.instructions}
            </p>
          </CardContent>
        </Card>
      ) : null}

      {iv.events.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Events Timeline</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col divide-y">
              {iv.events.map((ev) => (
                <div
                  key={ev.id}
                  className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium">{ev.description}</p>
                    {ev.actor_name ? (
                      <p className="text-xs text-muted-foreground">
                        by {ev.actor_name}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <Badge variant="outline" className="text-xs">
                      {ev.event_type.replace(/_/g, " ")}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(ev.created_at)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : null}

      <RescheduleInterviewDialog
        interview={iv}
        open={rescheduleOpen}
        onOpenChange={setRescheduleOpen}
        onSuccess={(message) => {
          setSuccessMessage(message);
        }}
      />
    </div>
  );
}

function ScoreCard({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {label}
        </p>
        <p className="mt-1 font-mono text-2xl font-semibold">
          {formatScore(value)}
        </p>
      </CardContent>
    </Card>
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
      <span className="w-32 shrink-0 font-medium text-muted-foreground">
        {label}
      </span>
      <span className="text-foreground">{children}</span>
    </div>
  );
}
