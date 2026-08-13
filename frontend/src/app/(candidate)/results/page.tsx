"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  GraduationCap,
  Trophy,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  useAssignedResults,
  usePracticeResults,
} from "@/features/candidate/hooks";
import type {
  AssignedResultListItem,
  PracticeResultListItem,
} from "@/features/candidate/types";
import { cn } from "@/lib/utils";
import { formatDate, formatDuration, formatScore, scoreTone } from "@/lib/format";
import { ROUTES } from "@/lib/constants";

const PAGE_SIZE = 10;

export default function ResultsPage() {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="flex items-center gap-2">
        <Button asChild variant="ghost" size="icon" className="h-8 w-8">
          <Link href={ROUTES.candidate.dashboard}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Results</h1>
          <p className="text-sm text-muted-foreground">
            All your completed interview evaluations.
          </p>
        </div>
      </div>

      <Tabs defaultValue="practice" className="w-full">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="practice" className="gap-1.5">
            <GraduationCap className="h-4 w-4" />
            Practice Results
          </TabsTrigger>
          <TabsTrigger value="assigned" className="gap-1.5">
            <Trophy className="h-4 w-4" />
            Assigned Results
          </TabsTrigger>
        </TabsList>

        <TabsContent value="practice" className="mt-6">
          <PracticeResultsTab />
        </TabsContent>
        <TabsContent value="assigned" className="mt-6">
          <AssignedResultsTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function PracticeResultsTab() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, refetch } = usePracticeResults(
    page,
    PAGE_SIZE,
  );

  if (isLoading) return <ListLoading />;
  if (isError) return <ListError onRetry={() => refetch()} />;
  if (!data || data.items.length === 0) {
    return (
      <EmptyResults
        icon={<GraduationCap className="h-10 w-10 text-muted-foreground" />}
        title="No practice results yet"
        message="Complete a practice interview to see your results here."
        cta={
          <Button asChild variant="outline">
            <Link href={ROUTES.candidate.dashboard}>
              Start a Practice Interview
            </Link>
          </Button>
        }
      />
    );
  }

  const totalPages = Math.ceil(data.total / data.page_size);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {data.total} practice interview{data.total !== 1 ? "s" : ""} completed
      </p>

      <div className="space-y-3">
        {data.items.map((item) => (
          <PracticeResultCard key={item.interview_id} item={item} />
        ))}
      </div>

      {totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  );
}

function AssignedResultsTab() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, refetch } = useAssignedResults(
    page,
    PAGE_SIZE,
  );

  if (isLoading) return <ListLoading />;
  if (isError) return <ListError onRetry={() => refetch()} />;
  if (!data || data.items.length === 0) {
    return (
      <EmptyResults
        icon={<Trophy className="h-10 w-10 text-muted-foreground" />}
        title="No assigned results yet"
        message="Results from admin-assigned interviews will appear here once they are evaluated."
      />
    );
  }

  const totalPages = Math.ceil(data.total / data.page_size);

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {data.total} assigned interview{data.total !== 1 ? "s" : ""} completed
      </p>

      <div className="space-y-3">
        {data.items.map((item) => (
          <AssignedResultCard key={item.interview_id} item={item} />
        ))}
      </div>

      {totalPages > 1 && (
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      )}
    </div>
  );
}

function PracticeResultCard({ item }: { item: PracticeResultListItem }) {
  const tone = scoreTone(item.overall_score);
  const toneClass = {
    muted: "text-muted-foreground",
    danger: "text-destructive",
    warn: "text-amber-600 dark:text-amber-400",
    ok: "text-primary",
    great: "text-emerald-600 dark:text-emerald-400",
  }[tone];

  return (
    <Card>
      <CardContent className="p-4 sm:p-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="truncate font-medium text-foreground">
                {item.role ?? "Practice Interview"}
              </h3>
              <Badge variant="outline" className="shrink-0 text-xs">
                {item.practice_type === "ROLE_BASED" ? "Role" : "JD"}
              </Badge>
            </div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
              <span>{formatDate(item.completed_at)}</span>
              {item.duration_minutes && (
                <span>{formatDuration(item.duration_minutes)}</span>
              )}
              {item.ai_verdict && (
                <VerdictBadge verdict={item.ai_verdict} />
              )}
            </div>
          </div>

          <div className="flex items-center gap-4 sm:text-right">
            <div>
              <p className={cn("text-2xl font-bold", toneClass)}>
                {formatScore(item.overall_score)}
              </p>
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                Overall
              </p>
            </div>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <ScoreChip label="Technical" value={item.technical_score} />
          <ScoreChip label="Communication" value={item.communication_score} />
          <ScoreChip label="Reasoning" value={item.reasoning_score} />
          <ScoreChip label="Project" value={item.project_knowledge_score} />
        </div>

        {(item.strengths.length > 0 || item.weaknesses.length > 0) && (
          <>
            <Separator className="my-3" />
            <div className="grid gap-2 sm:grid-cols-2">
              {item.strengths.length > 0 && (
                <div className="space-y-1">
                  {item.strengths.slice(0, 2).map((s, i) => (
                    <p
                      key={i}
                      className="text-xs text-emerald-600 dark:text-emerald-400"
                    >
                      ✓ {s}
                    </p>
                  ))}
                </div>
              )}
              {item.weaknesses.length > 0 && (
                <div className="space-y-1">
                  {item.weaknesses.slice(0, 2).map((w, i) => (
                    <p
                      key={i}
                      className="text-xs text-amber-600 dark:text-amber-400"
                    >
                      ! {w}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        <div className="mt-3 flex justify-end">
          {item.session_id && (
            <Button asChild size="sm" variant="outline">
              <Link href={ROUTES.candidate.practiceResult(item.session_id)}>
                View Full Report
              </Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function AssignedResultCard({ item }: { item: AssignedResultListItem }) {
  const decisionVariant: "success" | "destructive" | "warning" | "outline" =
    item.admin_decision === "CLEARED"
      ? "success"
      : item.admin_decision === "NOT_CLEARED"
        ? "destructive"
        : "outline";

  const decisionLabel =
    item.admin_decision === "CLEARED"
      ? "Cleared"
      : item.admin_decision === "NOT_CLEARED"
        ? "Not Cleared"
        : "Awaiting decision";

  return (
    <Card>
      <CardContent className="p-4 sm:p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="truncate font-medium text-foreground">
                {item.role ?? "Assigned Interview"}
              </h3>
              <Badge variant={decisionVariant} className="shrink-0">
                {decisionLabel}
              </Badge>
            </div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
              <span>{formatDate(item.completed_at)}</span>
              {item.duration_minutes && (
                <span>{formatDuration(item.duration_minutes)}</span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-lg font-semibold">
                {formatScore(item.ai_overall_score)}
              </p>
              <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
                AI Score
              </p>
            </div>
            {item.ai_verdict && <VerdictBadge verdict={item.ai_verdict} />}
          </div>
        </div>

        {item.admin_feedback && (
          <>
            <Separator className="my-3" />
            <p className="line-clamp-2 text-xs text-muted-foreground">
              <span className="font-medium text-foreground">Feedback:</span>{" "}
              {item.admin_feedback}
            </p>
          </>
        )}

        <div className="mt-3 flex justify-end">
          {item.session_id && (
            <Button asChild size="sm" variant="outline">
              <Link href={ROUTES.candidate.assignedResult(item.session_id)}>
                View Full Report
              </Link>
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function ScoreChip({
  label,
  value,
}: {
  label: string;
  value: string | null;
}) {
  const tone = scoreTone(value);
  const toneClass = {
    muted: "text-muted-foreground",
    danger: "text-destructive",
    warn: "text-amber-600 dark:text-amber-400",
    ok: "text-primary",
    great: "text-emerald-600 dark:text-emerald-400",
  }[tone];

  return (
    <div className="rounded-md border px-2.5 py-1.5">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className={cn("text-sm font-semibold", toneClass)}>
        {formatScore(value)}
      </p>
    </div>
  );
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const variant: "success" | "destructive" | "warning" | "outline" =
    verdict === "CLEARED"
      ? "success"
      : verdict === "NOT_CLEARED"
        ? "destructive"
        : verdict === "BORDERLINE"
          ? "warning"
          : "outline";

  const label =
    verdict === "CLEARED"
      ? "Cleared"
      : verdict === "NOT_CLEARED"
        ? "Not Cleared"
        : verdict === "BORDERLINE"
          ? "Borderline"
          : verdict;

  return <Badge variant={variant}>{label}</Badge>;
}

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
        <Skeleton key={k} className="h-32 w-full rounded-lg" />
      ))}
    </div>
  );
}

function ListError({ onRetry }: { onRetry: () => void }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
        <p className="text-sm text-destructive">
          Failed to load your results.
        </p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      </CardContent>
    </Card>
  );
}

function EmptyResults({
  icon,
  title,
  message,
  cta,
}: {
  icon: React.ReactNode;
  title: string;
  message: string;
  cta?: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 p-12 text-center">
        {icon}
        <h2 className="text-lg font-medium">{title}</h2>
        <p className="max-w-md text-sm text-muted-foreground">{message}</p>
        {cta}
      </CardContent>
    </Card>
  );
}
