"use client";

import { useState } from "react";
import Link from "next/link";
import { Eye } from "lucide-react";

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
import { useEvaluations } from "@/features/admin/hooks";
import { ROUTES } from "@/lib/constants";
import { formatDateTime, formatScore } from "@/lib/format";

function verdictVariant(
  verdict: string | null,
): "default" | "secondary" | "destructive" | "outline" {
  if (!verdict) return "outline";
  const map: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    CLEARED: "default",
    NOT_CLEARED: "destructive",
    BORDERLINE: "secondary",
    NEEDS_REVIEW: "secondary",
    NEEDS_FURTHER_REVIEW: "secondary",
  };
  return map[verdict] ?? "outline";
}

type ReviewTab = "pending" | "completed";

export default function EvaluationsPage() {
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState<ReviewTab>("pending");
  const pageSize = 20;

  const { data, isLoading } = useEvaluations({
    page,
    page_size: pageSize,
    review_state: tab,
  });

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;
  const isCompleted = tab === "completed";

  function switchTab(next: ReviewTab) {
    setTab(next);
    setPage(1);
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Evaluations
        </h1>
        <p className="text-sm text-muted-foreground">
          Review AI-evaluated interviews and submit your final decision.
        </p>
      </header>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-base">
              {isCompleted ? "Completed Reviews" : "Pending Review"}
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                size="sm"
                variant={tab === "pending" ? "default" : "outline"}
                onClick={() => switchTab("pending")}
              >
                Pending
              </Button>
              <Button
                type="button"
                size="sm"
                variant={tab === "completed" ? "default" : "outline"}
                onClick={() => switchTab("completed")}
              >
                Completed
              </Button>
            </div>
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
              {isCompleted
                ? "No completed evaluations yet."
                : "No evaluations pending review."}
            </p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Candidate</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>AI Score</TableHead>
                      <TableHead>AI Verdict</TableHead>
                      {isCompleted ? (
                        <TableHead>Admin Decision</TableHead>
                      ) : null}
                      <TableHead>Submitted</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.items.map((ev) => (
                      <TableRow key={ev.session_id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">
                              {ev.candidate_name}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {ev.candidate_email}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>{ev.role ?? "—"}</TableCell>
                        <TableCell className="font-mono">
                          {formatScore(ev.ai_overall_score)}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={verdictVariant(ev.ai_verdict)}
                            className="text-xs"
                          >
                            {ev.ai_verdict?.replace(/_/g, " ") ?? "—"}
                          </Badge>
                        </TableCell>
                        {isCompleted ? (
                          <TableCell>
                            <Badge
                              variant={verdictVariant(ev.admin_decision)}
                              className="text-xs"
                            >
                              {ev.admin_decision?.replace(/_/g, " ") ?? "—"}
                            </Badge>
                          </TableCell>
                        ) : null}
                        <TableCell className="text-muted-foreground">
                          {formatDateTime(ev.submitted_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="icon" asChild title="View">
                            <Link
                              href={`${ROUTES.admin.evaluations}/${ev.session_id}`}
                            >
                              <Eye className="h-4 w-4" />
                            </Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="mt-4 flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  Showing {data.items.length} of {data.total}
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
