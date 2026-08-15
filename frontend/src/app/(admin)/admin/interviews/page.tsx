"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { CalendarClock, ClipboardCheck, Eye, PlusCircle, Search, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
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
import { MobileField } from "@/components/admin/mobile-field";
import { RescheduleInterviewDialog } from "@/components/admin/reschedule-interview-dialog";
import { useCancelInterview, useInterviews } from "@/features/admin/hooks";
import type { InterviewListItem } from "@/features/admin/types";
import { ROUTES } from "@/lib/constants";
import { formatDateTime, formatDuration, formatScore } from "@/lib/format";

const QUICK_FILTERS = [
  { label: "All", value: "" },
  { label: "In Progress", value: "IN_PROGRESS_GROUP" },
  { label: "Completed", value: "COMPLETED_GROUP" },
  { label: "Missed", value: "MISSED_GROUP" },
  { label: "Cancelled", value: "CANCELLED_GROUP" },
] as const;

const NON_CANCELLABLE = new Set(["CANCELLED", "COMPLETED", "EXPIRED"]);
const EVALUATION_STATUSES = new Set([
  "AI_EVALUATED",
  "ADMIN_REVIEW",
  "COMPLETED",
]);

function statusVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  const map: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    COMPLETED: "default",
    IN_PROGRESS: "secondary",
    CANCELLED: "destructive",
    EXPIRED: "destructive",
    RESCHEDULED: "secondary",
    SUBMITTED: "secondary",
    AI_EVALUATED: "secondary",
    ADMIN_REVIEW: "secondary",
  };
  return map[status] ?? "outline";
}

export default function InterviewsPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64 w-full" />
        </div>
      }
    >
      <InterviewsPageContent />
    </Suspense>
  );
}

function InterviewsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState(
    () => searchParams.get("status") ?? "",
  );
  const [typeFilter, setTypeFilter] = useState("");
  const pageSize = 20;

  useEffect(() => {
    const fromUrl = searchParams.get("status") ?? "";
    setStatusFilter(fromUrl);
    setPage(1);
  }, [searchParams]);

  const { data, isLoading } = useInterviews({
    page,
    page_size: pageSize,
    search: search || undefined,
    status: statusFilter || undefined,
    interview_type: typeFilter || undefined,
  });

  const cancel = useCancelInterview();
  const [rescheduleTarget, setRescheduleTarget] =
    useState<InterviewListItem | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  function applyStatusFilter(value: string) {
    setStatusFilter(value);
    setPage(1);
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set("status", value);
    } else {
      params.delete("status");
    }
    const qs = params.toString();
    router.replace(
      qs ? `${ROUTES.admin.interviews}?${qs}` : ROUTES.admin.interviews,
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Interviews
          </h1>
          <p className="text-sm text-muted-foreground">
            View and manage all interviews.
          </p>
          {successMessage ? (
            <p className="mt-2 text-sm text-emerald-600 dark:text-emerald-400">
              {successMessage}
            </p>
          ) : null}
        </div>
        <Button asChild className="w-full sm:w-auto">
          <Link href={ROUTES.admin.assign}>
            <PlusCircle className="mr-2 h-4 w-4" />
            Assign Interview
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2 pb-3">
            {QUICK_FILTERS.map((f) => (
              <Button
                key={f.label}
                type="button"
                size="sm"
                variant={statusFilter === f.value ? "default" : "outline"}
                onClick={() => applyStatusFilter(f.value)}
              >
                {f.label}
              </Button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by candidate or role..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="pl-9"
              />
            </div>
            <select
              value={
                [
                  "",
                  "DRAFT",
                  "ASSIGNED",
                  "SCHEDULED",
                  "AVAILABLE",
                  "IN_PROGRESS",
                  "SUBMITTED",
                  "AI_EVALUATED",
                  "ADMIN_REVIEW",
                  "COMPLETED",
                  "CANCELLED",
                  "EXPIRED",
                  "RESCHEDULED",
                ].includes(statusFilter)
                  ? statusFilter
                  : ""
              }
              onChange={(e) => applyStatusFilter(e.target.value)}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="ASSIGNED">Assigned</option>
              <option value="SCHEDULED">Scheduled</option>
              <option value="AVAILABLE">Available</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="AI_EVALUATED">AI Evaluated</option>
              <option value="ADMIN_REVIEW">Admin Review</option>
              <option value="COMPLETED">Completed</option>
              <option value="CANCELLED">Cancelled</option>
              <option value="EXPIRED">Missed</option>
              <option value="RESCHEDULED">Rescheduled</option>
            </select>
            <select
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">All Types</option>
              <option value="PRACTICE">Practice</option>
              <option value="ASSIGNED">Assigned</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !data || data.items.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No interviews found.
            </p>
          ) : (
            <>
              {/* Desktop table (md+) */}
              <div className="hidden overflow-x-auto md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Candidate</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Scheduled</TableHead>
                      <TableHead>Started</TableHead>
                      <TableHead>Completed</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Score</TableHead>
                      <TableHead>Assigned By</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.items.map((iv) => {
                      const badgeLabel = (
                        iv.display_status ?? iv.status
                      ).replace(/_/g, " ");
                      const canCancel = !NON_CANCELLABLE.has(iv.status);
                      const canReview =
                        !!iv.session_id &&
                        EVALUATION_STATUSES.has(iv.status);

                      return (
                        <TableRow key={iv.id}>
                          <TableCell>
                            <div>
                              <p className="font-medium">{iv.candidate_name}</p>
                              <p className="text-xs text-muted-foreground">
                                {iv.candidate_email}
                              </p>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-xs">
                              {iv.interview_type}
                              {iv.practice_type
                                ? ` / ${iv.practice_type.replace("_", " ")}`
                                : ""}
                            </Badge>
                          </TableCell>
                          <TableCell>{iv.role ?? "—"}</TableCell>
                          <TableCell>
                            <Badge
                              variant={statusVariant(iv.status)}
                              className="text-xs"
                            >
                              {badgeLabel}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {formatDateTime(iv.scheduled_at)}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {formatDateTime(iv.started_at)}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {formatDateTime(iv.completed_at)}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {formatDuration(iv.duration_minutes)}
                          </TableCell>
                          <TableCell className="font-mono text-muted-foreground">
                            {formatScore(iv.overall_score)}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {iv.assigned_by_name ?? "—"}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="icon"
                                asChild
                                title="View Interview"
                              >
                                <Link
                                  href={`${ROUTES.admin.interviews}/${iv.id}`}
                                >
                                  <Eye className="h-4 w-4" />
                                </Link>
                              </Button>
                              {canReview ? (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  asChild
                                  title="Review Evaluation"
                                >
                                  <Link
                                    href={`${ROUTES.admin.evaluations}/${iv.session_id}`}
                                  >
                                    <ClipboardCheck className="h-4 w-4" />
                                  </Link>
                                </Button>
                              ) : null}
                              {iv.can_reschedule ? (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  title="Reschedule Interview"
                                  onClick={() => setRescheduleTarget(iv)}
                                >
                                  <CalendarClock className="mr-1.5 h-4 w-4" />
                                  Reschedule
                                </Button>
                              ) : null}
                              {canCancel ? (
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  title="Cancel Interview"
                                  onClick={() => cancel.mutate(iv.id)}
                                  disabled={cancel.isPending}
                                >
                                  <XCircle className="h-4 w-4 text-destructive" />
                                </Button>
                              ) : null}
                            </div>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile card list (<md) */}
              <div className="flex flex-col gap-3 md:hidden">
                {data.items.map((iv) => {
                  const badgeLabel = (iv.display_status ?? iv.status).replace(
                    /_/g,
                    " ",
                  );
                  const canCancel = !NON_CANCELLABLE.has(iv.status);
                  const canReview =
                    !!iv.session_id && EVALUATION_STATUSES.has(iv.status);
                  return (
                    <div
                      key={iv.id}
                      className="flex flex-col gap-3 rounded-lg border bg-card p-4"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate font-medium">
                            {iv.candidate_name}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">
                            {iv.candidate_email}
                          </p>
                        </div>
                        <Badge
                          variant={statusVariant(iv.status)}
                          className="text-xs"
                        >
                          {badgeLabel}
                        </Badge>
                      </div>

                      <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
                        <MobileField label="Role" value={iv.role ?? "—"} />
                        <MobileField
                          label="Type"
                          value={
                            iv.interview_type +
                            (iv.practice_type
                              ? ` / ${iv.practice_type.replace("_", " ")}`
                              : "")
                          }
                        />
                        <MobileField
                          label="Scheduled"
                          value={formatDateTime(iv.scheduled_at)}
                        />
                        <MobileField
                          label="Duration"
                          value={formatDuration(iv.duration_minutes)}
                        />
                        <MobileField
                          label="Started"
                          value={formatDateTime(iv.started_at)}
                        />
                        <MobileField
                          label="Completed"
                          value={formatDateTime(iv.completed_at)}
                        />
                        <MobileField
                          label="Score"
                          value={formatScore(iv.overall_score)}
                        />
                        <MobileField
                          label="Assigned By"
                          value={iv.assigned_by_name ?? "—"}
                        />
                      </div>

                      <div className="flex flex-wrap gap-2 pt-1">
                        <Button
                          variant="outline"
                          size="sm"
                          asChild
                          className="flex-1"
                        >
                          <Link href={`${ROUTES.admin.interviews}/${iv.id}`}>
                            <Eye className="mr-1.5 h-4 w-4" />
                            View
                          </Link>
                        </Button>
                        {canReview ? (
                          <Button
                            variant="outline"
                            size="sm"
                            asChild
                            className="flex-1"
                          >
                            <Link
                              href={`${ROUTES.admin.evaluations}/${iv.session_id}`}
                            >
                              <ClipboardCheck className="mr-1.5 h-4 w-4" />
                              Review
                            </Link>
                          </Button>
                        ) : null}
                        {iv.can_reschedule ? (
                          <Button
                            variant="outline"
                            size="sm"
                            className="flex-1"
                            onClick={() => setRescheduleTarget(iv)}
                          >
                            <CalendarClock className="mr-1.5 h-4 w-4" />
                            Reschedule
                          </Button>
                        ) : null}
                        {canCancel ? (
                          <Button
                            variant="outline"
                            size="sm"
                            className="flex-1 text-destructive hover:text-destructive"
                            onClick={() => cancel.mutate(iv.id)}
                            disabled={cancel.isPending}
                          >
                            <XCircle className="mr-1.5 h-4 w-4" />
                            Cancel
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-muted-foreground">
                  Showing {data.items.length} of {data.total} interviews
                </p>
                <div className="flex items-center justify-between gap-2 sm:justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {page} / {totalPages || 1}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <RescheduleInterviewDialog
        interview={rescheduleTarget}
        open={rescheduleTarget !== null}
        onOpenChange={(next) => {
          if (!next) setRescheduleTarget(null);
        }}
        onSuccess={(message) => {
          setSuccessMessage(message);
        }}
      />
    </div>
  );
}
