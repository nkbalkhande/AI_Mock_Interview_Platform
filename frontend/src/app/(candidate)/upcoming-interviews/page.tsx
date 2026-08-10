"use client";

import Link from "next/link";
import {
  ArrowLeft,
  CalendarClock,
  Clock,
  PlayCircle,
  Search,
} from "lucide-react";

import { InterviewStatusBadge } from "@/components/dashboard/interview-status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useUpcomingInterviews } from "@/features/candidate/hooks";
import type { UpcomingInterview } from "@/features/candidate/types";
import { formatDate, formatDuration, formatTime } from "@/lib/format";
import { ROUTES } from "@/lib/constants";
import { useState } from "react";

export default function UpcomingInterviewsPage() {
  const { data, isLoading, isError, refetch } = useUpcomingInterviews(100);
  const items = data?.items ?? [];
  const [search, setSearch] = useState("");

  const filtered = items.filter((item) => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      item.role?.toLowerCase().includes(q) ||
      item.job_description?.toLowerCase().includes(q) ||
      item.status?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" size="icon" className="h-8 w-8">
              <Link href={ROUTES.candidate.dashboard}>
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <h1 className="text-2xl font-semibold tracking-tight">
              Upcoming Interviews
            </h1>
          </div>
          <p className="mt-1 pl-10 text-sm text-muted-foreground">
            All interviews assigned to you by your interviewer or admin.
          </p>
        </div>
      </div>

      {items.length > 3 && (
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by role or keywords..."
            className="pl-9"
          />
        </div>
      )}

      {isLoading ? (
        <LoadingState />
      ) : isError ? (
        <ErrorState onRetry={() => refetch()} />
      ) : filtered.length === 0 ? (
        search.trim() ? (
          <NoResultsState onClear={() => setSearch("")} />
        ) : (
          <EmptyState />
        )
      ) : (
        <>
          <DesktopTable items={filtered} />
          <MobileList items={filtered} />
        </>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-3">
      {[0, 1, 2, 3, 4].map((k) => (
        <Skeleton key={k} className="h-16 w-full rounded-lg" />
      ))}
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
        <p className="text-sm text-destructive">
          Failed to load your upcoming interviews.
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
        <CalendarClock className="h-10 w-10 text-muted-foreground" />
        <h2 className="text-lg font-medium">No upcoming interviews</h2>
        <p className="max-w-md text-sm text-muted-foreground">
          When an admin or interviewer assigns you an interview, it will appear
          here. You&apos;ll also receive a notification.
        </p>
        <Button asChild variant="outline" className="mt-2">
          <Link href={ROUTES.candidate.interviews}>
            Try a Practice Interview
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

function NoResultsState({ onClear }: { onClear: () => void }) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
        <Search className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          No interviews match your search.
        </p>
        <Button variant="ghost" size="sm" onClick={onClear}>
          Clear search
        </Button>
      </CardContent>
    </Card>
  );
}

function ActionButton({ item }: { item: UpcomingInterview }) {
  if (item.access_state === "OPEN") {
    return (
      <Button asChild size="sm">
        <Link href={ROUTES.candidate.upcomingDetail(item.id)}>
          <PlayCircle className="mr-1 h-3.5 w-3.5" />
          View & Join
        </Link>
      </Button>
    );
  }
  if (item.access_state === "CLOSED") {
    return (
      <Button size="sm" variant="outline" disabled>
        Window closed
      </Button>
    );
  }
  return (
    <Button asChild size="sm" variant="outline">
      <Link href={ROUTES.candidate.upcomingDetail(item.id)}>
        <Clock className="mr-1 h-3.5 w-3.5" />
        View Details
      </Link>
    </Button>
  );
}

function ExperienceRange({ item }: { item: UpcomingInterview }) {
  const min = item.required_experience_min;
  const max = item.required_experience_max;
  if (!min && !max) return null;
  const label =
    min && max
      ? `${min}–${max} yrs`
      : min
        ? `${min}+ yrs`
        : `Up to ${max} yrs`;
  return (
    <Badge variant="outline" className="whitespace-nowrap text-xs">
      {label}
    </Badge>
  );
}

function DesktopTable({ items }: { items: UpcomingInterview[] }) {
  return (
    <Card className="hidden md:block">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Role / Description</TableHead>
            <TableHead>Date & Time</TableHead>
            <TableHead>Duration</TableHead>
            <TableHead>Experience</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id}>
              <TableCell className="max-w-[300px]">
                <div className="flex flex-col gap-0.5">
                  <span className="font-medium text-foreground">
                    {item.role ?? "Assigned Interview"}
                  </span>
                  {item.job_description && (
                    <span className="line-clamp-1 text-xs text-muted-foreground">
                      {item.job_description}
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell className="whitespace-nowrap">
                <div className="flex flex-col gap-0.5">
                  <span className="text-sm">
                    {formatDate(item.scheduled_at)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatTime(item.scheduled_at)}
                  </span>
                </div>
              </TableCell>
              <TableCell>{formatDuration(item.duration_minutes)}</TableCell>
              <TableCell>
                <ExperienceRange item={item} />
              </TableCell>
              <TableCell>
                <InterviewStatusBadge status={item.status} />
              </TableCell>
              <TableCell className="text-right">
                <ActionButton item={item} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
}

function MobileList({ items }: { items: UpcomingInterview[] }) {
  return (
    <div className="space-y-3 md:hidden">
      {items.map((item) => (
        <Card key={item.id}>
          <CardContent className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-foreground">
                  {item.role ?? "Assigned Interview"}
                </p>
                {item.job_description && (
                  <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                    {item.job_description}
                  </p>
                )}
              </div>
              <InterviewStatusBadge status={item.status} />
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <CalendarClock className="h-3 w-3" />
                {formatDate(item.scheduled_at)}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {formatTime(item.scheduled_at)}
              </span>
              <span>{formatDuration(item.duration_minutes)}</span>
              <ExperienceRange item={item} />
            </div>

            <div className="mt-3">
              <ActionButton item={item} />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
