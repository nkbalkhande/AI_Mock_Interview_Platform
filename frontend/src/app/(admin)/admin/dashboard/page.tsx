"use client";

import {
  CheckCircle2,
  ClipboardCheck,
  ListChecks,
  Users,
} from "lucide-react";

import { StatCard } from "@/components/dashboard/stat-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAdminDashboard } from "@/features/admin/hooks";
import { formatDateTime } from "@/lib/format";

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
        <StatCard
          label="Total Interviews"
          value={stats?.total_interviews ?? 0}
          icon={ListChecks}
          isLoading={isLoading}
          hint="All types combined"
        />
        <StatCard
          label="Pending Evaluations"
          value={stats?.pending_evaluations ?? 0}
          icon={ClipboardCheck}
          isLoading={isLoading}
          accent="warning"
          hint="Awaiting admin review"
        />
        <StatCard
          label="Completed"
          value={stats?.completed_interviews ?? 0}
          icon={CheckCircle2}
          isLoading={isLoading}
          accent="success"
          hint="Fully processed"
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
              {data?.recent_activity.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">
                      {item.description}
                    </p>
                    {item.actor_name ? (
                      <p className="text-xs text-muted-foreground">
                        by {item.actor_name}
                      </p>
                    ) : null}
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <Badge variant="outline" className="text-xs">
                      {item.event_type.replace(/_/g, " ")}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(item.created_at)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
