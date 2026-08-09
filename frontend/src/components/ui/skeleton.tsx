import * as React from "react";

import { cn } from "@/lib/utils";

/** Placeholder block for content that's still loading. */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-muted-foreground/10",
        className,
      )}
      {...props}
    />
  );
}

export { Skeleton };
