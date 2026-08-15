"use client";

import { useEffect, useState } from "react";
import { CalendarClock, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRescheduleInterview } from "@/features/admin/hooks";
import { formatDateTime } from "@/lib/format";

export interface RescheduleTarget {
  id: string;
  candidate_name: string;
  role: string | null;
  scheduled_at: string | null;
  status: string;
  display_status: string | null;
  duration_minutes: number;
  timezone: string | null;
}

function splitLocal(value: string | null): { date: string; time: string } {
  if (!value) return { date: "", time: "" };
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return { date: "", time: "" };
  const pad = (n: number) => String(n).padStart(2, "0");
  return {
    date: `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
    time: `${pad(date.getHours())}:${pad(date.getMinutes())}`,
  };
}

export function RescheduleInterviewDialog({
  interview,
  open,
  onOpenChange,
  onSuccess,
}: {
  interview: RescheduleTarget | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (message: string) => void;
}) {
  const mutation = useRescheduleInterview();
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [duration, setDuration] = useState(30);
  const [timezone, setTimezone] = useState("UTC");
  const [reason, setReason] = useState("Candidate missed scheduled interview");
  const [notify, setNotify] = useState(true);

  useEffect(() => {
    if (!interview || !open) return;
    const next = splitLocal(interview.scheduled_at);
    setDate(next.date);
    setTime(next.time);
    setDuration(interview.duration_minutes || 30);
    setTimezone(interview.timezone || "UTC");
    setReason("Candidate missed scheduled interview");
    setNotify(true);
    mutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reset form when a different interview opens
  }, [interview?.id, open]);

  async function handleConfirm() {
    if (!interview || !date || !time) return;
    const local = new Date(`${date}T${time}`);
    if (Number.isNaN(local.getTime()) || local.getTime() <= Date.now()) {
      return;
    }
    try {
      const result = await mutation.mutateAsync({
        interviewId: interview.id,
        new_scheduled_at: local.toISOString(),
        reason: reason.trim() || null,
        notify_candidate: notify,
        duration_minutes: duration,
        timezone,
      });
      onOpenChange(false);
      onSuccess?.(
        result.notification_sent
          ? result.message
          : `${result.message} Candidate notification could not be sent.`,
      );
    } catch {
      // surfaced via mutation.error
    }
  }

  const localValue = date && time ? new Date(`${date}T${time}`) : null;
  const isPast = !!localValue && localValue.getTime() <= Date.now();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100vh-2rem)] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Reschedule Interview</DialogTitle>
          <DialogDescription>
            Choose a new date and time for this missed interview.
          </DialogDescription>
        </DialogHeader>

        {interview ? (
          <div className="space-y-4">
            <div className="rounded-md border bg-muted/40 p-3 text-sm">
              <p>
                <span className="text-muted-foreground">Candidate: </span>
                {interview.candidate_name}
              </p>
              <p>
                <span className="text-muted-foreground">Position: </span>
                {interview.role ?? "Assigned interview"}
              </p>
              <p className="mt-2 flex items-center gap-1.5">
                <CalendarClock className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="text-muted-foreground">Previous schedule:</span>
                {formatDateTime(interview.scheduled_at)}
              </p>
              <p>
                <span className="text-muted-foreground">Status: </span>
                {interview.display_status ?? "Missed"}
              </p>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor="reschedule-date">New Date</Label>
                <Input
                  id="reschedule-date"
                  type="date"
                  className="mt-1"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                />
              </div>
              <div>
                <Label htmlFor="reschedule-time">New Time</Label>
                <Input
                  id="reschedule-time"
                  type="time"
                  className="mt-1"
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <Label htmlFor="reschedule-duration">Duration (minutes)</Label>
                <Input
                  id="reschedule-duration"
                  type="number"
                  min={15}
                  max={180}
                  className="mt-1"
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                />
              </div>
              <div>
                <Label htmlFor="reschedule-timezone">Timezone</Label>
                <Input
                  id="reschedule-timezone"
                  className="mt-1"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                />
              </div>
            </div>

            {isPast ? (
              <p className="text-xs text-destructive">
                New date/time cannot be in the past.
              </p>
            ) : null}

            <div>
              <Label htmlFor="reschedule-reason">Reason (optional)</Label>
              <textarea
                id="reschedule-reason"
                rows={3}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>

            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={notify}
                onChange={(e) => setNotify(e.target.checked)}
              />
              Notify candidate
            </label>

            {mutation.isError ? (
              <p className="text-sm text-destructive">
                {mutation.error.message ?? "Could not reschedule this interview."}
              </p>
            ) : null}
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!interview || !date || !time || isPast || mutation.isPending}
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving…
              </>
            ) : (
              "Confirm Reschedule"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
