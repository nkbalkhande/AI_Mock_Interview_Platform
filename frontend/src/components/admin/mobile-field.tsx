import { cn } from "@/lib/utils";

interface MobileFieldProps {
  label: string;
  value: React.ReactNode;
  className?: string;
}

/**
 * Compact label/value pair used inside the mobile card layouts of admin
 * list pages (candidates, interviews, evaluations). Wraps values so long
 * strings like emails or datetimes don't force horizontal scroll.
 */
export function MobileField({ label, value, className }: MobileFieldProps) {
  return (
    <div className={cn("min-w-0", className)}>
      <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-0.5 break-words text-sm">{value}</p>
    </div>
  );
}
