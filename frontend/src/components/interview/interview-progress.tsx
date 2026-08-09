import { cn } from "@/lib/utils";

interface InterviewProgressProps {
  currentNumber: number;
  totalQuestions: number;
  answeredCount: number;
  className?: string;
}

/**
 * Compact progress readout — "Question 3 of 6" with a filled bar showing
 * how many questions the candidate has answered so far.
 */
export function InterviewProgress({
  currentNumber,
  totalQuestions,
  answeredCount,
  className,
}: InterviewProgressProps) {
  const pct = totalQuestions
    ? Math.min(100, Math.round((answeredCount / totalQuestions) * 100))
    : 0;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-baseline justify-between text-xs font-medium text-muted-foreground">
        <span className="text-foreground">
          Question {currentNumber} of {totalQuestions}
        </span>
        <span>
          {answeredCount} / {totalQuestions} answered
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 w-full overflow-hidden rounded-full bg-secondary"
      >
        <div
          className="h-full rounded-full bg-primary transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
