import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number | null | undefined;
  icon: LucideIcon;
  hint?: string;
  isLoading?: boolean;
  accent?: "primary" | "success" | "warning";
}

const ACCENTS: Record<NonNullable<StatCardProps["accent"]>, string> = {
  primary: "bg-primary/10 text-primary",
  success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
};

/** Single top-of-dashboard stat tile (Practice / Upcoming / Completed / Avg). */
export function StatCard({
  label,
  value,
  icon: Icon,
  hint,
  isLoading,
  accent = "primary",
}: StatCardProps) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div
          className={cn(
            "grid h-11 w-11 shrink-0 place-items-center rounded-lg",
            ACCENTS[accent],
          )}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          {isLoading ? (
            <Skeleton className="mt-1 h-7 w-16" />
          ) : (
            <p className="mt-0.5 text-2xl font-semibold text-foreground">
              {value ?? "—"}
            </p>
          )}
          {hint ? (
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {hint}
            </p>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
