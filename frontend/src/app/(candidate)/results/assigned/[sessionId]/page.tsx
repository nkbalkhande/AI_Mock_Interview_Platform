"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  CheckCircle2,
  Clock,
  History,
  RefreshCw,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAssignedResultDetail } from "@/features/candidate/hooks";
import { ROUTES } from "@/lib/constants";

/**
 * Assigned interview result page.
 *
 * Candidates land here right after submitting an assigned interview. Unlike
 * practice interviews there is no instant AI report: the result stays in
 * "pending review" until the interviewer publishes a final decision, at
 * which point this page shows the decision, feedback, and AI assessment.
 */
export default function AssignedResultPage() {
  const params = useParams<{ sessionId: string }>();
  const result = useAssignedResultDetail(params?.sessionId ?? null);

  if (result.isLoading) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-4">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (result.isError || !result.data) {
    return (
      <StateCard
        icon={<RefreshCw className="h-7 w-7" />}
        title="Result unavailable"
        message={result.error?.message || "We could not load this result."}
        action={<Button onClick={() => result.refetch()}>Try again</Button>}
      />
    );
  }

  const report = result.data;

  if (report.status === "PENDING_REVIEW") {
    return (
      <StateCard
        icon={<Clock className="h-7 w-7" />}
        title="Interview submitted"
        message={
          `Your ${report.role ? `${report.role} ` : ""}interview has been ` +
          "submitted and is now with the interviewer for review. You'll be " +
          "notified when the final result is published — it will appear " +
          "under Assigned Interview Results."
        }
        action={
          <div className="flex flex-col gap-2 sm:flex-row">
            <Button asChild variant="outline">
              <Link href={ROUTES.candidate.interviewHistory}>
                <History className="mr-2 h-4 w-4" /> Interview history
              </Link>
            </Button>
            <Button asChild>
              <Link href={ROUTES.candidate.dashboard}>
                <CheckCircle2 className="mr-2 h-4 w-4" /> Back to dashboard
              </Link>
            </Button>
          </div>
        }
      />
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <header className="flex flex-col gap-3 rounded-xl border bg-card p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">
            Assigned interview{report.role ? ` — ${report.role}` : ""}
          </p>
          <h1 className="text-2xl font-semibold">Interview Result</h1>
          {report.assigned_by_name ? (
            <p className="mt-1 text-sm text-muted-foreground">
              Assigned by {report.assigned_by_name}
            </p>
          ) : null}
        </div>
        <DecisionBadge decision={report.admin_decision} />
      </header>

      <section className="grid gap-3 sm:grid-cols-2">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">AI assessment score</p>
            <p className="mt-1 text-2xl font-semibold">
              {formatScore(report.ai_overall_score)}
              <span className="ml-1 text-sm font-normal text-muted-foreground">
                / 10
              </span>
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Result published</p>
            <p className="mt-1 text-2xl font-semibold">
              {formatDate(report.result_published_at)}
            </p>
            {report.decided_by_name ? (
              <p className="mt-1 text-xs text-muted-foreground">
                Reviewed by {report.decided_by_name}
              </p>
            ) : null}
          </CardContent>
        </Card>
      </section>

      {report.admin_feedback ? (
        <Card>
          <CardHeader>
            <h2 className="font-semibold">Interviewer feedback</h2>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">
              {report.admin_feedback}
            </p>
          </CardContent>
        </Card>
      ) : null}

      {report.ai_summary ? (
        <Card>
          <CardHeader>
            <h2 className="font-semibold">Assessment summary</h2>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">
              {report.ai_summary}
            </p>
          </CardContent>
        </Card>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-3">
        <FeedbackCard title="Strong areas" items={report.strengths} />
        <FeedbackCard title="Needs improvement" items={report.weaknesses} />
        <FeedbackCard
          title="Areas to work on"
          items={report.improvement_areas}
        />
      </section>

      <div className="flex justify-end">
        <Button asChild>
          <Link href={ROUTES.candidate.dashboard}>
            <CheckCircle2 className="mr-2 h-4 w-4" /> Back to dashboard
          </Link>
        </Button>
      </div>
    </div>
  );
}

function DecisionBadge({ decision }: { decision: string | null }) {
  if (decision === "CLEARED") {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-4 py-2 text-sm font-semibold text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300">
        <CheckCircle2 className="h-4 w-4" /> Cleared
      </span>
    );
  }
  if (decision === "NOT_CLEARED") {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-red-100 px-4 py-2 text-sm font-semibold text-red-800 dark:bg-red-900/40 dark:text-red-300">
        <XCircle className="h-4 w-4" /> Not Cleared
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-4 py-2 text-sm font-semibold text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
      <Clock className="h-4 w-4" /> Under Further Review
    </span>
  );
}

function FeedbackCard({ title, items }: { title: string; items: string[] }) {
  return (
    <Card>
      <CardHeader>
        <h2 className="font-semibold">{title}</h2>
      </CardHeader>
      <CardContent>
        {items.length ? (
          <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
            {items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No items reported.</p>
        )}
      </CardContent>
    </Card>
  );
}

function StateCard({
  icon,
  title,
  message,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  message: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mx-auto grid min-h-[50vh] max-w-lg place-items-center">
      <Card className="w-full">
        <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
          <span className="text-primary">{icon}</span>
          <h1 className="text-xl font-semibold">{title}</h1>
          <p className="text-sm text-muted-foreground">{message}</p>
          {action}
        </CardContent>
      </Card>
    </div>
  );
}

function formatScore(value: string | null) {
  if (value == null) return "—";
  const parsed = Number(value);
  return Number.isNaN(parsed) ? value : parsed.toFixed(1);
}

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
