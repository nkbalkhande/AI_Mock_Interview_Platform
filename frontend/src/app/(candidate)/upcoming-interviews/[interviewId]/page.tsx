"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Briefcase,
  CalendarClock,
  Clock,
  FileText,
  Loader2,
  PlayCircle,
  User,
} from "lucide-react";

import { InterviewStatusBadge } from "@/components/dashboard/interview-status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useUpcomingInterviewDetail } from "@/features/candidate/hooks";
import type { UpcomingInterviewDetail } from "@/features/candidate/types";
import { useStartAssignedInterview } from "@/features/interviews/hooks";
import { formatDate, formatDuration, formatTime } from "@/lib/format";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

export default function UpcomingInterviewDetailPage() {
  const params = useParams<{ interviewId: string }>();
  const interviewId = params?.interviewId ?? null;

  const { data, isLoading, isError, refetch } =
    useUpcomingInterviewDetail(interviewId);

  if (isLoading) return <DetailLoading />;
  if (isError || !data) {
    return <DetailError onRetry={() => refetch()} />;
  }

  return <InterviewDetailBody data={data} />;
}

function InterviewDetailBody({ data }: { data: UpcomingInterviewDetail }) {
  const isOpen = data.access_state === "OPEN";
  const isClosed = data.access_state === "CLOSED";
  const isPending = data.access_state === "PENDING";
  const canJoin = isOpen || data.status === "IN_PROGRESS";
  const start = useStartAssignedInterview();
  const router = useRouter();

  async function handleStart() {
    try {
      const result = await start.mutateAsync(data.id);
      router.push(ROUTES.candidate.interview(result.session_id));
    } catch {
      // Error is rendered from start.error below.
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-2">
        <Button asChild variant="ghost" size="icon" className="h-8 w-8 shrink-0">
          <Link href={ROUTES.candidate.upcoming}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-semibold tracking-tight sm:text-2xl">
            {data.role ?? "Assigned Interview"}
          </h1>
        </div>
        <InterviewStatusBadge status={data.status} />
      </div>

      {/* Access Window Banner */}
      {canJoin && (
        <div className="flex flex-col gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-900 dark:bg-emerald-950/30 sm:flex-row sm:items-center">
          <PlayCircle className="h-5 w-5 shrink-0 text-emerald-600 dark:text-emerald-400" />
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-emerald-800 dark:text-emerald-200">
              {data.status === "IN_PROGRESS"
                ? "Interview in progress"
                : "Interview window is open"}
            </p>
            <p className="text-xs text-emerald-700 dark:text-emerald-300">
              {data.status === "IN_PROGRESS"
                ? "You can continue this interview now."
                : "You can start this interview now."}
              {data.access_end_at && data.status !== "IN_PROGRESS" && (
                <> Window closes at {formatTime(data.access_end_at)}.</>
              )}
            </p>
          </div>
          <StartAssignedButton
            interview={data}
            size="sm"
            isPending={start.isPending}
            errorMessage={start.error?.message}
            onStart={handleStart}
            className="w-full sm:w-auto"
          />
        </div>
      )}

      {isPending && !canJoin && (
        <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-900 dark:bg-blue-950/30">
          <Clock className="h-5 w-5 shrink-0 text-blue-600 dark:text-blue-400" />
          <div className="flex-1">
            <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
              Interview not yet available
            </p>
            <p className="text-xs text-blue-700 dark:text-blue-300">
              {data.access_start_at ? (
                <>
                  Access opens at {formatTime(data.access_start_at)} on{" "}
                  {formatDate(data.access_start_at)}.
                </>
              ) : (
                <>The interview will become available at the scheduled time.</>
              )}
            </p>
          </div>
        </div>
      )}

      {isClosed && !canJoin && (
        <div className="flex items-center gap-3 rounded-lg border border-destructive/20 bg-destructive/5 p-4">
          <Clock className="h-5 w-5 shrink-0 text-destructive" />
          <div className="flex-1">
            <p className="text-sm font-medium text-destructive">
              Interview window has closed
            </p>
            <p className="text-xs text-destructive/80">
              The access period for this interview has ended. Contact your
              interviewer if you need a reschedule.
            </p>
          </div>
        </div>
      )}

      {/* Interview Details */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Interview Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <DetailItem
              icon={<CalendarClock className="h-4 w-4" />}
              label="Scheduled Date"
              value={formatDate(data.scheduled_at)}
            />
            <DetailItem
              icon={<Clock className="h-4 w-4" />}
              label="Scheduled Time"
              value={formatTime(data.scheduled_at)}
            />
            <DetailItem
              icon={<Clock className="h-4 w-4" />}
              label="Duration"
              value={formatDuration(data.duration_minutes)}
            />
            <DetailItem
              icon={<Briefcase className="h-4 w-4" />}
              label="Required Experience"
              value={formatExperience(
                data.required_experience_min,
                data.required_experience_max,
              )}
            />
            {data.assigned_by_name && (
              <DetailItem
                icon={<User className="h-4 w-4" />}
                label="Assigned By"
                value={data.assigned_by_name}
              />
            )}
            {data.timezone && (
              <DetailItem
                icon={<Clock className="h-4 w-4" />}
                label="Timezone"
                value={data.timezone}
              />
            )}
          </div>

          {data.access_start_at && data.access_end_at && (
            <>
              <Separator />
              <div>
                <p className="text-xs font-medium text-muted-foreground">
                  Access Window
                </p>
                <p className="mt-1 text-sm">
                  {formatDate(data.access_start_at)},{" "}
                  {formatTime(data.access_start_at)} –{" "}
                  {formatTime(data.access_end_at)}
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Job Description */}
      {data.job_description && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" />
              Job Description
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap text-sm text-muted-foreground">
              {data.job_description}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Instructions */}
      {data.instructions && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Instructions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="whitespace-pre-wrap text-sm text-muted-foreground">
              {data.instructions}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Bottom CTA */}
      {canJoin && (
        <div className="flex justify-stretch pb-4 sm:justify-end">
          <StartAssignedButton
            interview={data}
            size="lg"
            isPending={start.isPending}
            errorMessage={start.error?.message}
            onStart={handleStart}
            className="w-full sm:w-auto"
          />
        </div>
      )}
    </div>
  );
}

function StartAssignedButton({
  interview,
  size,
  isPending,
  errorMessage,
  onStart,
  className,
}: {
  interview: UpcomingInterviewDetail;
  size: "sm" | "lg";
  isPending: boolean;
  errorMessage?: string;
  onStart: () => void;
  className?: string;
}) {
  const label =
    interview.status === "IN_PROGRESS" ? "Continue Interview" : "Join Interview";

  return (
    <div className={cn("flex flex-col items-stretch gap-2 sm:items-end", className)}>
      {errorMessage ? (
        <p className="text-xs text-destructive sm:max-w-xs sm:text-right">
          {errorMessage}
        </p>
      ) : null}
      <Button
        size={size}
        onClick={onStart}
        disabled={isPending}
        aria-busy={isPending}
        className="w-full sm:w-auto"
      >
        {isPending ? (
          <>
            <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
            Starting…
          </>
        ) : (
          <>
            <PlayCircle className={size === "lg" ? "mr-2 h-4 w-4" : "mr-1 h-3.5 w-3.5"} />
            {size === "lg" && interview.status !== "IN_PROGRESS"
              ? "Start Interview"
              : label}
          </>
        )}
      </Button>
    </div>
  );
}

function DetailItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-0.5 text-muted-foreground">{icon}</div>
      <div>
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="text-sm font-medium">{value}</p>
      </div>
    </div>
  );
}

function formatExperience(
  min: string | null,
  max: string | null,
): string {
  if (!min && !max) return "Not specified";
  if (min && max) return `${min}–${max} years`;
  if (min) return `${min}+ years`;
  return `Up to ${max} years`;
}

function DetailLoading() {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <div className="flex items-center gap-3">
        <Skeleton className="h-8 w-8" />
        <Skeleton className="h-8 w-60" />
      </div>
      <Skeleton className="h-16 w-full rounded-lg" />
      <Skeleton className="h-48 w-full rounded-lg" />
      <Skeleton className="h-32 w-full rounded-lg" />
    </div>
  );
}

function DetailError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="mx-auto w-full max-w-3xl">
      <Card>
        <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
          <p className="text-sm text-destructive">
            Could not load interview details.
          </p>
          <div className="flex gap-2">
            <Button asChild variant="outline" size="sm">
              <Link href={ROUTES.candidate.upcoming}>
                <ArrowLeft className="mr-1 h-3.5 w-3.5" />
                Back to list
              </Link>
            </Button>
            <Button variant="outline" size="sm" onClick={onRetry}>
              Try again
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
