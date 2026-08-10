"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useInterviewDetail } from "@/features/admin/hooks";
import { ROUTES } from "@/lib/constants";
import { formatDateTime, formatDuration } from "@/lib/format";

export default function InterviewDetailPage({
  params,
}: {
  params: Promise<{ interviewId: string }>;
}) {
  const { interviewId } = use(params);
  const { data: iv, isLoading } = useInterviewDetail(interviewId);

  if (isLoading) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!iv) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center gap-4 py-20">
        <p className="text-muted-foreground">Interview not found.</p>
        <Button variant="outline" asChild>
          <Link href={ROUTES.admin.interviews}>Back to Interviews</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href={ROUTES.admin.interviews}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Interview Details
          </h1>
          <p className="text-sm text-muted-foreground">
            {iv.role ?? "N/A"} &middot; {iv.candidate_name}
          </p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Interview Info</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <Row label="Type">
              <Badge variant="outline">{iv.interview_type}</Badge>
              {iv.practice_type ? (
                <Badge variant="secondary" className="ml-1">
                  {iv.practice_type.replace("_", " ")}
                </Badge>
              ) : null}
            </Row>
            <Row label="Role">{iv.role ?? "—"}</Row>
            <Row label="Status">
              <Badge variant="outline">
                {iv.status.replace(/_/g, " ")}
              </Badge>
            </Row>
            <Row label="Duration">{formatDuration(iv.duration_minutes)}</Row>
            <Row label="Scheduled">{formatDateTime(iv.scheduled_at)}</Row>
            <Row label="Timezone">{iv.timezone ?? "—"}</Row>
            <Row label="Access Window">
              {iv.access_start_at && iv.access_end_at
                ? `${formatDateTime(iv.access_start_at)} — ${formatDateTime(iv.access_end_at)}`
                : "—"}
            </Row>
            <Row label="Assigned By">{iv.assigned_by_name ?? "—"}</Row>
            <Row label="Created">{formatDateTime(iv.created_at)}</Row>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Candidate</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            <Row label="Name">{iv.candidate_name}</Row>
            <Row label="Email">{iv.candidate_email}</Row>
            {iv.required_experience_min != null ||
            iv.required_experience_max != null ? (
              <Row label="Required Experience">
                {iv.required_experience_min ?? "0"}–
                {iv.required_experience_max ?? "N/A"} yrs
              </Row>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {iv.job_description ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Job Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">
              {iv.job_description}
            </p>
          </CardContent>
        </Card>
      ) : null}

      {iv.instructions ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Instructions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm text-muted-foreground">
              {iv.instructions}
            </p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2">
      <span className="w-32 shrink-0 font-medium text-muted-foreground">
        {label}
      </span>
      <span className="text-foreground">{children}</span>
    </div>
  );
}
