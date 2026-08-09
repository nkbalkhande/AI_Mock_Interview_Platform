import type { ReactNode } from "react";

import { APP_NAME } from "@/lib/constants";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-background px-4 py-12">
      {/* Ambient background: fine grid + a single soft brand spotlight */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,var(--color-border)_1px,transparent_1px),linear-gradient(to_bottom,var(--color-border)_1px,transparent_1px)] bg-[size:44px_44px] opacity-60 [mask-image:radial-gradient(ellipse_55%_55%_at_50%_40%,black,transparent)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-1/3 h-[460px] w-[460px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/10 blur-[120px]"
      />

      <div className="relative mb-8 text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          {APP_NAME}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Practice and assigned AI-driven technical interviews.
        </p>
      </div>

      <div className="relative w-full">{children}</div>
    </div>
  );
}
