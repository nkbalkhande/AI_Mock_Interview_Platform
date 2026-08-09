"use client";

import Link from "next/link";
import { GraduationCap, ScrollText, Trophy } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useRecentResults } from "@/features/candidate/hooks";
import type {
  AssignedResultSummary,
  PracticeResultSummary,
} from "@/features/candidate/types";
import { ROUTES } from "@/lib/constants";
import { formatDate, formatScore, scoreTone } from "@/lib/format";
import { cn } from "@/lib/utils";

const LIMIT_PER_TYPE = 3;

/** Recent Results section — practice + assigned side-by-side (stacked on mobile). */
export function RecentResultsSection() {
  const { data, isLoading, isError, refetch } = useRecentResults(LIMIT_PER_TYPE);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base">Recent Results</CardTitle>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Your latest completed interviews.
          </p>
        </div>
        <Button asChild variant="ghost" size="sm">
          <Link href={ROUTES.candidate.results}>View all</Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <ResultsLoading />
        ) : isError ? (
          <ResultsError onRetry={() => refetch()} />
        ) : (data?.practice.length ?? 0) === 0 &&
          (data?.assigned.length ?? 0) === 0 ? (
          <ResultsEmpty />
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            <PracticeColumn items={data?.practice ?? []} />
            <AssignedColumn items={data?.assigned ?? []} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ResultsLoading() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {[0, 1].map((k) => (
        <div key={k} className="space-y-3">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ))}
    </div>
  );
}

function ResultsError({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-2 py-8 text-center">
      <p className="text-sm text-destructive">Couldn't load your results.</p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}

function ResultsEmpty() {
  return (
    <div className="flex flex-col items-center gap-2 py-8 text-center">
      <ScrollText className="h-8 w-8 text-muted-foreground" />
      <p className="text-sm font-medium text-foreground">
        No completed interviews yet
      </p>
      <p className="max-w-sm text-xs text-muted-foreground">
        Practice or assigned interview results will show here once you finish
        your first session.
      </p>
    </div>
  );
}

function ColumnHeader({
  icon: Icon,
  label,
}: {
  icon: typeof GraduationCap;
  label: string;
}) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Icon className="h-4 w-4 text-primary" />
      <h3 className="text-sm font-semibold text-foreground">{label}</h3>
    </div>
  );
}

function ScoreTone({
  score,
  label,
}: {
  score: string | null;
  label: string;
}) {
  const tone = scoreTone(score);
  const toneClass = {
    muted: "text-muted-foreground",
    danger: "text-destructive",
    warn: "text-amber-600 dark:text-amber-400",
    ok: "text-primary",
    great: "text-emerald-600 dark:text-emerald-400",
  }[tone];
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className={cn("mt-0.5 text-sm font-semibold", toneClass)}>
        {formatScore(score)}
      </p>
    </div>
  );
}

function PracticeCard({ item }: { item: PracticeResultSummary }) {
  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">
            {item.role ?? "Practice interview"}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {formatDate(item.completed_at)}
          </p>
        </div>
        <Badge variant="outline">Practice</Badge>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2">
        <ScoreTone score={item.overall_score} label="Overall" />
        <ScoreTone score={item.technical_score} label="Technical" />
        <ScoreTone score={item.communication_score} label="Communication" />
      </div>

      {(item.strengths.length > 0 || item.weaknesses.length > 0) && (
        <>
          <Separator className="my-3" />
          <div className="space-y-1.5 text-xs">
            {item.strengths.slice(0, 2).map((s, i) => (
              <p
                key={`s-${i}`}
                className="text-emerald-600 dark:text-emerald-400"
              >
                ✓ {s}
              </p>
            ))}
            {item.weaknesses.slice(0, 2).map((w, i) => (
              <p key={`w-${i}`} className="text-amber-600 dark:text-amber-400">
                ! {w}
              </p>
            ))}
          </div>
        </>
      )}

      <div className="mt-3 flex justify-end">
        {item.session_id ? (
          <Button asChild size="sm" variant="ghost">
            <Link href={ROUTES.candidate.practiceResult(item.session_id)}>
              View Result
            </Link>
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function AssignedCard({ item }: { item: AssignedResultSummary }) {
  const decisionVariant: "success" | "destructive" | "warning" | "outline" =
    item.admin_decision === "CLEARED"
      ? "success"
      : item.admin_decision === "NOT_CLEARED"
        ? "destructive"
        : item.admin_decision === "NEEDS_FURTHER_REVIEW"
          ? "warning"
          : "outline";

  const decisionLabel =
    item.admin_decision === "CLEARED"
      ? "Cleared"
      : item.admin_decision === "NOT_CLEARED"
        ? "Not Cleared"
        : item.admin_decision === "NEEDS_FURTHER_REVIEW"
          ? "Under review"
          : "Awaiting decision";

  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-foreground">
            {item.role ?? "Assigned interview"}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {formatDate(item.completed_at)}
          </p>
        </div>
        <Badge variant={decisionVariant}>{decisionLabel}</Badge>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <ScoreTone score={item.ai_overall_score} label="AI score" />
        <div>
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
            AI verdict
          </p>
          <p className="mt-0.5 text-sm font-semibold text-foreground">
            {item.ai_verdict ?? "—"}
          </p>
        </div>
      </div>

      {item.admin_feedback ? (
        <>
          <Separator className="my-3" />
          <p className="line-clamp-3 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Feedback:</span>{" "}
            {item.admin_feedback}
          </p>
        </>
      ) : null}

      <div className="mt-3 flex justify-end">
        {item.session_id ? (
          <Button asChild size="sm" variant="ghost">
            <Link href={ROUTES.candidate.assignedResult(item.session_id)}>
              View Result
            </Link>
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function PracticeColumn({ items }: { items: PracticeResultSummary[] }) {
  return (
    <div>
      <ColumnHeader icon={GraduationCap} label="Practice" />
      {items.length === 0 ? (
        <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
          No practice results yet.
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <PracticeCard key={item.interview_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function AssignedColumn({ items }: { items: AssignedResultSummary[] }) {
  return (
    <div>
      <ColumnHeader icon={Trophy} label="Assigned" />
      {items.length === 0 ? (
        <p className="rounded-lg border border-dashed p-3 text-xs text-muted-foreground">
          No assigned results yet.
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <AssignedCard key={item.interview_id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}
