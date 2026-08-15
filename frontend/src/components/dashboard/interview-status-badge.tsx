import { Badge } from "@/components/ui/badge";

/** Human-friendly rendering for the ``interviews.status`` enum. */
const STATUS_LABELS: Record<string, string> = {
  DRAFT: "Draft",
  ASSIGNED: "Assigned",
  SCHEDULED: "Scheduled",
  AVAILABLE: "Available",
  IN_PROGRESS: "In progress",
  SUBMITTED: "Submitted",
  AI_EVALUATED: "Evaluated",
  ADMIN_REVIEW: "Under review",
  COMPLETED: "Completed",
  CANCELLED: "Cancelled",
  EXPIRED: "Missed",
  RESCHEDULED: "Rescheduled",
};

const STATUS_VARIANTS: Record<
  string,
  "default" | "secondary" | "success" | "warning" | "destructive" | "outline"
> = {
  DRAFT: "outline",
  ASSIGNED: "secondary",
  SCHEDULED: "secondary",
  AVAILABLE: "success",
  IN_PROGRESS: "warning",
  SUBMITTED: "warning",
  AI_EVALUATED: "default",
  ADMIN_REVIEW: "default",
  COMPLETED: "success",
  CANCELLED: "destructive",
  EXPIRED: "destructive",
  RESCHEDULED: "warning",
};

export function InterviewStatusBadge({ status }: { status: string }) {
  const label = STATUS_LABELS[status] ?? status;
  const variant = STATUS_VARIANTS[status] ?? "outline";
  return <Badge variant={variant}>{label}</Badge>;
}
