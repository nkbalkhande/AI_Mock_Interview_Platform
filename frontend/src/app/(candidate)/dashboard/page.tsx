"use client";

import { CalendarClock, CheckCircle2, GraduationCap, Trophy } from "lucide-react";

import { QuickActionsSection } from "@/components/dashboard/quick-actions-section";
import { RecentResultsSection } from "@/components/dashboard/recent-results-section";
import { StatCard } from "@/components/dashboard/stat-card";
import { UpcomingInterviewsSection } from "@/components/dashboard/upcoming-interviews-section";
import { useCandidateDashboard } from "@/features/candidate/hooks";
import { useAuth } from "@/hooks/use-auth";
import { formatScore } from "@/lib/format";

function firstName(fullName: string | undefined | null): string {
  if (!fullName) return "there";
  const [first] = fullName.trim().split(/\s+/);
  return first || fullName;
}

export default function CandidateDashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, isError, refetch } = useCandidateDashboard();

  const stats = data?.stats;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Welcome, {firstName(user?.fullName)}{" "}
          <span aria-hidden="true">👋</span>
        </h1>
        <p className="text-sm text-muted-foreground">
          Your Interview Overview
        </p>
      </header>

      {isError ? (
        <div className="flex items-center justify-between rounded-md border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm">
          <span className="text-destructive">
            Couldn&apos;t load your dashboard.
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
        aria-label="Interview stats"
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <StatCard
          label="Practice Interviews"
          value={stats?.practice_interviews ?? 0}
          icon={GraduationCap}
          isLoading={isLoading}
          hint="Self-serve practice runs"
        />
        <StatCard
          label="Upcoming Interviews"
          value={stats?.upcoming_interviews ?? 0}
          icon={CalendarClock}
          isLoading={isLoading}
          accent="warning"
          hint="Scheduled by an admin"
        />
        <StatCard
          label="Completed Interviews"
          value={stats?.completed_interviews ?? 0}
          icon={CheckCircle2}
          isLoading={isLoading}
          accent="success"
          hint="Practice + assigned"
        />
        <StatCard
          label="Average Score"
          value={
            stats?.average_practice_score
              ? formatScore(stats.average_practice_score)
              : "—"
          }
          icon={Trophy}
          isLoading={isLoading}
          hint="Practice progress"
        />
      </section>

      <UpcomingInterviewsSection />

      <RecentResultsSection />

      <section aria-label="Quick actions" className="flex flex-col gap-3">
        <div>
          <h2 className="text-base font-semibold text-foreground">
            Quick Actions
          </h2>
          <p className="text-xs text-muted-foreground">
            Jump into a self-serve practice interview.
          </p>
        </div>
        <QuickActionsSection />
      </section>
    </div>
  );
}
