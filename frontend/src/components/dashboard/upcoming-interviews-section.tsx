"use client";

import Link from "next/link";
import { CalendarClock, Clock, PlayCircle } from "lucide-react";

import { InterviewStatusBadge } from "@/components/dashboard/interview-status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

const LIMIT = 5;

/** Section listing the candidate's next assigned interviews. */
export function UpcomingInterviewsSection() {
  const { data, isLoading, isError, refetch } = useUpcomingInterviews(LIMIT);
  const items = data?.items ?? [];

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-base">Upcoming Interviews</CardTitle>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Assigned interviews you have coming up.
          </p>
        </div>
        <Button asChild variant="ghost" size="sm">
          <Link href={ROUTES.candidate.upcoming}>View all</Link>
        </Button>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <LoadingState />
        ) : isError ? (
          <ErrorState onRetry={() => refetch()} />
        ) : items.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <MobileList items={items} />
            <DesktopTable items={items} />
          </>
        )}
      </CardContent>
    </Card>
  );
}

function LoadingState() {
  return (
    <div className="space-y-3 p-4">
      {[0, 1, 2].map((k) => (
        <Skeleton key={k} className="h-14 w-full" />
      ))}
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-2 p-8 text-center">
      <p className="text-sm text-destructive">
        Couldn't load your upcoming interviews.
      </p>
      <Button variant="outline" size="sm" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-2 p-8 text-center">
      <CalendarClock className="h-8 w-8 text-muted-foreground" />
      <p className="text-sm font-medium text-foreground">
        No upcoming interviews yet
      </p>
      <p className="max-w-sm text-xs text-muted-foreground">
        Assigned interviews will appear here. In the meantime, try a practice
        interview from the Quick Actions below.
      </p>
    </div>
  );
}

function JoinCta({ item }: { item: UpcomingInterview }) {
  if (item.access_state === "OPEN") {
    return (
      <Button asChild size="sm">
        <Link href={ROUTES.candidate.interview(item.id)}>
          <PlayCircle />
          Join Interview
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
    <Badge variant="outline" className="gap-1 whitespace-nowrap">
      <Clock className="h-3 w-3" />
      Scheduled
    </Badge>
  );
}

function DesktopTable({ items }: { items: UpcomingInterview[] }) {
  return (
    <div className="hidden md:block">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Role</TableHead>
            <TableHead>Date</TableHead>
            <TableHead>Time</TableHead>
            <TableHead>Duration</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => (
            <TableRow key={item.id}>
              <TableCell className="max-w-[260px]">
                <div className="flex flex-col gap-0.5">
                  <span className="font-medium text-foreground">
                    {item.role ?? "Assigned interview"}
                  </span>
                  {item.job_description ? (
                    <span className="line-clamp-1 text-xs text-muted-foreground">
                      {item.job_description}
                    </span>
                  ) : null}
                </div>
              </TableCell>
              <TableCell>{formatDate(item.scheduled_at)}</TableCell>
              <TableCell>{formatTime(item.scheduled_at)}</TableCell>
              <TableCell>{formatDuration(item.duration_minutes)}</TableCell>
              <TableCell>
                <InterviewStatusBadge status={item.status} />
              </TableCell>
              <TableCell className="text-right">
                <JoinCta item={item} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function MobileList({ items }: { items: UpcomingInterview[] }) {
  return (
    <ul className="divide-y md:hidden">
      {items.map((item) => (
        <li key={item.id} className="flex flex-col gap-2 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate font-medium text-foreground">
                {item.role ?? "Assigned interview"}
              </p>
              {item.job_description ? (
                <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                  {item.job_description}
                </p>
              ) : null}
            </div>
            <InterviewStatusBadge status={item.status} />
          </div>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>{formatDate(item.scheduled_at)}</span>
            <span>{formatTime(item.scheduled_at)}</span>
            <span>{formatDuration(item.duration_minutes)}</span>
          </div>
          <div className="pt-1">
            <JoinCta item={item} />
          </div>
        </li>
      ))}
    </ul>
  );
}
