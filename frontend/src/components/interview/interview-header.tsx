import Link from "next/link";
import { ArrowLeft, FileText, Sparkles } from "lucide-react";

import type { InterviewSummary } from "@/features/interviews/types";
import { Badge } from "@/components/ui/badge";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface InterviewHeaderProps {
  interview: InterviewSummary;
  className?: string;
}

const PRACTICE_LABEL: Record<string, string> = {
  JD_BASED: "JD-based practice",
  ROLE_BASED: "Role-based practice",
};

export function InterviewHeader({ interview, className }: InterviewHeaderProps) {
  const isPractice = interview.interview_type === "PRACTICE";
  const badgeLabel = isPractice
    ? PRACTICE_LABEL[interview.practice_type ?? ""] ?? "Practice"
    : "Assigned";
  return (
    <div
      className={cn(
        "flex flex-col gap-2 border-b border-border pb-4",
        className,
      )}
    >
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link
          href={ROUTES.candidate.dashboard}
          className="inline-flex items-center gap-1 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded"
          aria-label="Back to dashboard"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-primary/10 text-primary">
          {isPractice ? (
            <Sparkles className="h-4 w-4" />
          ) : (
            <FileText className="h-4 w-4" />
          )}
        </span>
        <div className="flex flex-col">
          <h1 className="text-lg font-semibold text-foreground">
            {interview.role_name ?? "Practice Interview"}
          </h1>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">{badgeLabel}</Badge>
            <span>Duration: {interview.duration_minutes} min</span>
          </div>
        </div>
      </div>
    </div>
  );
}
