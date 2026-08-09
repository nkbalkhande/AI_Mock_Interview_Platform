"use client";

import { useEffect, useRef, useState } from "react";
import { Clock } from "lucide-react";

import { cn } from "@/lib/utils";

interface InterviewTimerProps {
  /** Total duration of the interview, in minutes (from ``interview.duration_minutes``). */
  durationMinutes: number;
  /**
   * Optional absolute start timestamp (ISO). Used to keep the timer
   * consistent across refreshes; without it we start counting from mount.
   */
  startedAt?: string | null;
  className?: string;
}

/**
 * Client-side UX-only countdown.
 *
 * Per plan: timer enforcement is *not* server-side in this task. If the
 * candidate keeps working after 0:00 the backend will still accept
 * answers. We surface this as a hint, not a hard cutoff — a heartbeat
 * enforcement pass is a follow-up task.
 */
export function InterviewTimer({
  durationMinutes,
  startedAt,
  className,
}: InterviewTimerProps) {
  const startMs = useRef<number>(
    startedAt ? new Date(startedAt).getTime() : Date.now(),
  );
  const totalMs = durationMinutes * 60 * 1000;
  const [now, setNow] = useState<number>(Date.now());

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const elapsed = Math.max(0, now - startMs.current);
  const remaining = Math.max(0, totalMs - elapsed);
  const seconds = Math.floor(remaining / 1000) % 60;
  const minutes = Math.floor(remaining / (1000 * 60));

  const isWarning = remaining <= 5 * 60 * 1000 && remaining > 60 * 1000;
  const isCritical = remaining <= 60 * 1000;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-md border border-border bg-background px-3 py-1.5 text-sm font-medium",
        isWarning && "border-amber-500 text-amber-600 dark:text-amber-400",
        isCritical && "border-destructive text-destructive",
        className,
      )}
      aria-label="Remaining time"
    >
      <Clock className="h-4 w-4" aria-hidden="true" />
      <span className="tabular-nums">
        {minutes.toString().padStart(2, "0")}:{seconds.toString().padStart(2, "0")}
      </span>
    </div>
  );
}
