import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8 text-center">
      <div className="space-y-3">
        <h1 className="text-4xl font-bold tracking-tight">
          AI Mock Interview Platform
        </h1>
        <p className="text-muted-foreground max-w-md">
          Practice and assigned technical interviews with adaptive questioning
          and automated evaluation.
        </p>
      </div>
      <div className="flex gap-4">
        <Link
          href="/login"
          className="rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground"
        >
          Sign in
        </Link>
        <Link
          href="/register"
          className="rounded-md border px-5 py-2.5 text-sm font-medium"
        >
          Create account
        </Link>
      </div>
    </main>
  );
}
