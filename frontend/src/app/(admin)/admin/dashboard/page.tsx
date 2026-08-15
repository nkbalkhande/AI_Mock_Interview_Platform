"use client";

import Link from "next/link";
import {
  Ban,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  ListChecks,
  Sparkles,
  Users,
} from "lucide-react";

import { StatCard } from "@/components/dashboard/stat-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminDashboard } from "@/features/admin/hooks";
import { ROUTES } from "@/lib/constants";
import { formatDateTime, formatScore } from "@/lib/format";

function isEvaluationEvent(eventType: string): boolean {
  const t = eventType.toUpperCase();
  return (
    t.includes("EVALUAT") ||
    t.includes("ADMIN_DECISION") ||
    t.includes("ADMIN_REVIEW") ||
    t.includes("AI_EVALUATED")
  );
}

export default function AdminDashboardPage() {
  const { data, isLoading, isError, refetch } = useAdminDashboard();
  const stats = data?.stats;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Admin Dashboard
        </h1>
        <p className="text-sm text-muted-foreground">
          Overview of candidates, interviews, and evaluations.
        </p>
      </header>

      {isError ? (
        <div className="flex items-center justify-between rounded-md border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm">
          <span className="text-destructive">
            Couldn&apos;t load dashboard data.
          </span>
          <button
            onClick={() => refetch()}
            className="rounded-md px-3 py-1 text-xs font-medium text-destructive hover:bg-destructive/10"
          >
            Try again
          </button>
        </div>
      ) : null}

      <section
        aria-label="Dashboard stats"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <StatCard
          label="Total Candidates"
          value={stats?.total_candidates ?? 0}
          icon={Users}
          isLoading={isLoading}
          hint="Registered candidates"
        />
        <Link
          href={ROUTES.admin.interviews}
          className="rounded-lg transition-opacity hover:opacity-90"
        >
          <StatCard
            label="Total Interviews"
            value={stats?.total_interviews ?? 0}
            icon={ListChecks}
            isLoading={isLoading}
            hint="All types combined"
          />
        </Link>
        <Link
          href={ROUTES.admin.evaluations}
          className="rounded-lg transition-opacity hover:opacity-90"
        >
          <StatCard
            label="Pending Evaluations"
            value={stats?.pending_evaluations ?? 0}
            icon={ClipboardCheck}
            isLoading={isLoading}
            accent="warning"
            hint="Awaiting admin review"
          />
        </Link>
        <Link
          href={`${ROUTES.admin.interviews}?status=COMPLETED_GROUP`}
          className="rounded-lg transition-opacity hover:opacity-90"
        >
          <StatCard
            label="Completed"
            value={stats?.completed_interviews ?? 0}
            icon={CheckCircle2}
            isLoading={isLoading}
            accent="success"
            hint="Fully processed"
          />
        </Link>
        <Link
          href={`${ROUTES.admin.interviews}?status=IN_PROGRESS_GROUP`}
          className="rounded-lg transition-opacity hover:opacity-90"
        >
          <StatCard
            label="In Progress"
            value={stats?.in_progress_interviews ?? 0}
            icon={Clock}
            isLoading={isLoading}
            hint="Currently underway"
          />
        </Link>
        <StatCard
          label="Scheduled Upcoming"
          value={stats?.scheduled_upcoming ?? 0}
          icon={ListChecks}
          isLoading={isLoading}
          hint="Assigned & scheduled"
        />
        <Link
          href={`${ROUTES.admin.interviews}?status=CANCELLED_GROUP`}
          className="rounded-lg transition-opacity hover:opacity-90"
        >
          <StatCard
            label="Cancelled / Expired"
            value={stats?.cancelled_or_expired ?? 0}
            icon={Ban}
            isLoading={isLoading}
            accent="warning"
            hint="Terminal statuses"
          />
        </Link>
        <StatCard
          label="Avg AI Score"
          value={formatScore(stats?.average_ai_score)}
          icon={Sparkles}
          isLoading={isLoading}
          hint="Across evaluated sessions"
        />
      </section>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex flex-col gap-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : data?.recent_activity.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No recent activity yet.
            </p>
          ) : (
            <div className="flex flex-col divide-y">
              {data?.recent_activity.map((item) => {
                let href: string | null = null;
                if (
                  item.session_id &&
                  isEvaluationEvent(item.event_type)
                ) {
                  href = `${ROUTES.admin.evaluations}/${item.session_id}`;
                } else if (item.interview_id) {
                  href = `${ROUTES.admin.interviews}/${item.interview_id}`;
                }

                return (
                  <div
                    key={item.id}
                    className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between sm:gap-4"
                  >
                    <div className="min-w-0 flex-1">
                      {href ? (
                        <Link
                          href={href}
                          className="text-sm font-medium text-foreground hover:underline"
                        >
                          {item.description}
                        </Link>
                      ) : (
                        <p className="text-sm font-medium text-foreground">
                          {item.description}
                        </p>
                      )}
                      {item.actor_name ? (
                        <p className="text-xs text-muted-foreground">
                          by {item.actor_name}
                        </p>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap items-center gap-2 sm:shrink-0">
                      <Badge variant="outline" className="text-xs">
                        {item.event_type.replace(/_/g, " ")}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatDateTime(item.created_at)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
