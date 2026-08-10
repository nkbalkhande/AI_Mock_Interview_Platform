"use client";

import { useState } from "react";
import Link from "next/link";
import { Eye, PlusCircle, Search, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { useCancelInterview, useInterviews } from "@/features/admin/hooks";
import { ROUTES } from "@/lib/constants";
import { formatDateTime } from "@/lib/format";

function statusVariant(
  status: string,
): "default" | "secondary" | "destructive" | "outline" {
  const map: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    COMPLETED: "default",
    IN_PROGRESS: "secondary",
    CANCELLED: "destructive",
    EXPIRED: "destructive",
    SUBMITTED: "secondary",
    AI_EVALUATED: "secondary",
    ADMIN_REVIEW: "secondary",
  };
  return map[status] ?? "outline";
}

export default function InterviewsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const pageSize = 20;

  const { data, isLoading } = useInterviews({
    page,
    page_size: pageSize,
    search: search || undefined,
    status: statusFilter || undefined,
    interview_type: typeFilter || undefined,
  });

  const cancel = useCancelInterview();
  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Interviews
          </h1>
          <p className="text-sm text-muted-foreground">
            View and manage all interviews.
          </p>
        </div>
        <Button asChild>
          <Link href={ROUTES.admin.assign}>
            <PlusCircle className="mr-2 h-4 w-4" />
            Assign Interview
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
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
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
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
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Candidate</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Scheduled</TableHead>
                      <TableHead>Assigned By</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.items.map((iv) => (
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
                            {iv.status.replace(/_/g, " ")}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatDateTime(iv.scheduled_at)}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {iv.assigned_by_name ?? "—"}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="ghost" size="icon" asChild>
                              <Link
                                href={`${ROUTES.admin.interviews}/${iv.id}`}
                              >
                                <Eye className="h-4 w-4" />
                              </Link>
                            </Button>
                            {iv.status !== "CANCELLED" &&
                            iv.status !== "COMPLETED" ? (
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => cancel.mutate(iv.id)}
                                disabled={cancel.isPending}
                              >
                                <XCircle className="h-4 w-4 text-destructive" />
                              </Button>
                            ) : null}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="mt-4 flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  Showing {data.items.length} of {data.total} interviews
                </p>
                <div className="flex items-center gap-2">
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
    </div>
  );
}
