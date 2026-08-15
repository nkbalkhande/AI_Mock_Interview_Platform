"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowLeft,
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  Clock,
  Eye,
  History,
  OctagonX,
  PlayCircle,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useInterviewHistory } from "@/features/candidate/hooks";
import type { InterviewHistoryItem } from "@/features/candidate/types";
import { ROUTES } from "@/lib/constants";
import { formatDate, formatDuration, formatScore } from "@/lib/format";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 10;

type StatusFilter = "all" | "completed" | "in_progress" | "evaluating" | "incomplete";
type TypeFilter = "all" | "practice" | "assigned";

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "completed", label: "Completed" },
  { value: "in_progress", label: "In Progress" },
  { value: "evaluating", label: "Evaluating" },
  { value: "incomplete", label: "Incomplete" },
];

const TYPE_OPTIONS: { value: TypeFilter; label: string }[] = [
  { value: "all", label: "All Types" },
  { value: "practice", label: "Practice" },
  { value: "assigned", label: "Assigned" },
];

export default function InterviewHistoryPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");

  const { data, isLoading, isError, refetch } = useInterviewHistory(
    page,
    PAGE_SIZE,
    statusFilter === "all" ? null : statusFilter,
    typeFilter === "all" ? null : typeFilter,
  );

  const handleFilterChange = (
    setter: (v: never) => void,
    value: string,
  ) => {
    setter(value as never);
    setPage(1);
  };

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="flex items-center gap-2">
        <Button asChild variant="ghost" size="icon" className="h-8 w-8">
          <Link href={ROUTES.candidate.dashboard}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Interview History
          </h1>
          <p className="text-sm text-muted-foreground">
            Every interview you&apos;ve started or been assigned — completed and
            unfinished.
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex flex-wrap gap-1.5">
          {STATUS_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={statusFilter === opt.value ? "default" : "outline"}
              size="sm"
              onClick={() => handleFilterChange(setStatusFilter, opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
        <div className="hidden h-6 w-px bg-border sm:block" />
        <div className="flex flex-wrap gap-1.5">
          {TYPE_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={typeFilter === opt.value ? "default" : "outline"}
              size="sm"
              onClick={() => handleFilterChange(setTypeFilter, opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <ListLoading />
      ) : isError ? (
        <ListError onRetry={() => refetch()} />
      ) : !data || data.items.length === 0 ? (
        <EmptyState />
      ) : (
        <HistoryList data={data} page={page} onPageChange={setPage} />
      )}
    </div>
  );
}

function HistoryList({
  data,
  page,
  onPageChange,
}: {
  data: { items: InterviewHistoryItem[]; total: number; page_size: number };
  page: number;
  onPageChange: (p: number) => void;
}) {
  const totalPages = Math.ceil(data.total / data.page_size);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {data.total} interview{data.total !== 1 ? "s" : ""}
      </p>

      <div className="space-y-3">
        {data.items.map((item) => (
          <HistoryCard key={item.interview_id} item={item} />
        ))}
      </div>

      {totalPages > 1 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
}

function HistoryCard({ item }: { item: InterviewHistoryItem }) {
  const statusVariant = statusBadgeVariant(item.display_status);
  const isCompleted = item.display_status === "Completed";
  const isResumable = item.can_resume;

  return (
    <Card>
      <CardContent className="p-4 sm:p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          {/* Left: interview details */}
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate font-medium text-foreground">
                {item.role ?? "Interview"}
              </h3>
              <Badge variant="outline" className="shrink-0 text-xs">
                {item.interview_type === "ASSIGNED"
                  ? "Assigned"
                  : item.practice_type === "ROLE_BASED"
                    ? "Role Based"
                    : "JD Based"}
              </Badge>
              <Badge variant={statusVariant} className="shrink-0">
                {item.display_status}
              </Badge>
            </div>

            <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
              {item.started_at ? (
                <span>Started {formatDate(item.started_at)}</span>
              ) : item.display_status === "Not Started" ? (
                <span>Awaiting start</span>
              ) : item.display_status === "Cancelled" ? (
                <span>Cancelled {formatDate(item.last_activity_at)}</span>
              ) : null}
              {item.last_activity_at && item.display_status !== "Cancelled" && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Last activity {formatDate(item.last_activity_at)}
                </span>
              )}
              <span>{formatDuration(item.duration_minutes)}</span>
            </div>

            {item.total_questions > 0 && (
              <div className="mt-1.5 flex items-center gap-2">
                <div className="h-1.5 flex-1 rounded-full bg-muted">
                  <div
                    className={cn(
                      "h-1.5 rounded-full transition-all",
                      isCompleted ? "bg-emerald-500" : "bg-primary",
                    )}
                    style={{
                      width: `${Math.min(100, (item.answered_count / item.total_questions) * 100)}%`,
                    }}
                  />
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {item.answered_count}/{item.total_questions} answered
                </span>
              </div>
            )}
          </div>

          {/* Right: score + action */}
          <div className="flex items-center gap-4">
            {isCompleted && item.overall_score != null && (
              <div className="text-right">
                <p className="text-xl font-bold">
                  {formatScore(item.overall_score)}
                </p>
                <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                  Score
                </p>
              </div>
            )}

            <InterviewAction item={item} isCompleted={isCompleted} isResumable={isResumable} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function InterviewAction({
  item,
  isCompleted,
  isResumable,
}: {
  item: InterviewHistoryItem;
  isCompleted: boolean;
  isResumable: boolean;
}) {
  if (isCompleted && item.session_id) {
    const resultPath =
      item.interview_type === "ASSIGNED"
        ? ROUTES.candidate.assignedResult(item.session_id)
        : ROUTES.candidate.practiceResult(item.session_id);
    return (
      <Button asChild size="sm" variant="outline">
        <Link href={resultPath}>
          <Eye className="mr-1.5 h-4 w-4" />
          View Results
        </Link>
      </Button>
    );
  }

  if (isResumable && item.session_id) {
    return (
      <Button asChild size="sm" variant="default">
        <Link href={ROUTES.candidate.interview(item.session_id)}>
          <PlayCircle className="mr-1.5 h-4 w-4" />
          Resume
        </Link>
      </Button>
    );
  }

  if (
    item.display_status === "Interrupted" ||
    item.display_status === "Abandoned" ||
    item.display_status === "Expired" ||
    item.display_status === "Missed"
  ) {
    return (
      <Badge variant="destructive" className="text-xs">
        <OctagonX className="mr-1 h-3 w-3" />
        Interrupted
      </Badge>
    );
  }

  if (item.display_status === "Cancelled") {
    return (
      <Badge variant="destructive" className="text-xs">
        <XCircle className="mr-1 h-3 w-3" />
        Cancelled
      </Badge>
    );
  }

  if (item.display_status === "Rescheduled") {
    return (
      <Badge variant="outline" className="text-xs">
        <CalendarClock className="mr-1 h-3 w-3" />
        Rescheduled
      </Badge>
    );
  }

  if (item.display_status === "Not Started") {
    return (
      <Badge variant="outline" className="text-xs">
        <CalendarClock className="mr-1 h-3 w-3" />
        Not Started
      </Badge>
    );
  }

  if (
    item.display_status === "Evaluating" ||
    item.display_status === "Submitted"
  ) {
    return (
      <Badge variant="outline" className="text-xs">
        <Clock className="mr-1 h-3 w-3" />
        Awaiting Result
      </Badge>
    );
  }

  return null;
}

function statusBadgeVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  switch (status) {
    case "Completed":
      return "default";
    case "In Progress":
    case "Paused":
      return "secondary";
    case "Evaluating":
    case "Submitted":
      return "outline";
    case "Abandoned":
    case "Interrupted":
    case "Cancelled":
    case "Expired":
      return "destructive";
    default:
      return "outline";
  }
}

// ── Shared UI pieces ───────────────────────────────────────────────────

function Pagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="flex items-center justify-center gap-2 pt-4">
      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
      >
        <ChevronLeft className="h-4 w-4" />
        Previous
      </Button>
      <span className="text-sm text-muted-foreground">
        Page {page} of {totalPages}
      </span>
      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
      >
        Next
        <ChevronRight className="h-4 w-4" />
      </Button>
    </div>
  );
}

function ListLoading() {
  return (
    <div className="space-y-3">
      {[0, 1, 2, 3].map((k) => (
        <Skeleton key={k} className="h-28 w-full rounded-lg" />
      ))}
    </div>
  );
}

function ListError({ onRetry }: { onRetry: () => void }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
        <p className="text-sm text-destructive">
          Failed to load your interview history.
        </p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      </CardContent>
    </Card>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 p-12 text-center">
        <History className="h-10 w-10 text-muted-foreground" />
        <h2 className="text-lg font-medium">No interviews yet</h2>
        <p className="max-w-md text-sm text-muted-foreground">
          Start a practice interview to see your history here.
        </p>
        <Button asChild variant="outline">
          <Link href={ROUTES.candidate.dashboard}>
            Start a Practice Interview
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
