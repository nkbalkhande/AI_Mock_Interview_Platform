import Link from "next/link";

export default function HomePage() {
  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background p-6">
      {/* Ambient background: fine grid + a single soft brand spotlight */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,var(--color-border)_1px,transparent_1px),linear-gradient(to_bottom,var(--color-border)_1px,transparent_1px)] bg-[size:44px_44px] opacity-60 [mask-image:radial-gradient(ellipse_60%_60%_at_50%_45%,black,transparent)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-1/2 h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary/10 blur-[120px]"
      />

      {/* Square card — clean elevation, one accent line, no rainbow */}
      <div className="group relative aspect-square w-full max-w-md">
        <div className="relative flex h-full w-full flex-col items-center justify-center gap-8 overflow-hidden rounded-3xl border border-border bg-card/80 p-10 text-center shadow-[0_1px_0_0_oklch(1_0_0/0.06)_inset,0_24px_60px_-24px_oklch(0.2_0.02_264/0.35)] backdrop-blur-xl transition-all duration-500 hover:shadow-[0_1px_0_0_oklch(1_0_0/0.08)_inset,0_32px_80px_-24px_oklch(0.2_0.02_264/0.45)]">
          {/* hairline brand accent along the top edge */}
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent"
          />

          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary/60 px-3 py-1 text-xs font-medium text-muted-foreground">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
            </span>
            AI-Powered
          </span>

          <div className="space-y-4">
            <h1 className="text-4xl font-semibold leading-tight tracking-tight text-foreground">
              AI Mock Interview Platform
            </h1>
            <p className="mx-auto max-w-xs text-sm leading-relaxed text-muted-foreground">
              Practice and assigned technical interviews with adaptive
              questioning and automated evaluation.
            </p>
          </div>

          <div className="flex w-full flex-col gap-3 sm:flex-row sm:justify-center">
            <Link
              href="/login"
              className="inline-flex items-center justify-center rounded-lg bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-sm transition-all duration-200 hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="inline-flex items-center justify-center rounded-lg border border-border bg-transparent px-6 py-3 text-sm font-semibold text-foreground transition-all duration-200 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              Create account
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
