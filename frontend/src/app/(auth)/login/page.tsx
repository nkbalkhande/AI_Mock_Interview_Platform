"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLogin } from "@/features/auth/hooks";
import type { ApiError } from "@/features/auth/types";
import { loginSchema, type LoginFormValues } from "@/features/auth/validators";
import { dashboardPathForRoles } from "@/lib/auth";
import { ROUTES } from "@/lib/constants";

export default function LoginPage() {
  // Next 16 requires ``useSearchParams`` to sit inside a Suspense boundary so
  // the surrounding page can be pre-rendered statically. Wrapping the inner
  // form (which reads ``?redirect=``) keeps the static shell while deferring
  // the client-only search-param read to hydration.
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginForm />
    </Suspense>
  );
}

function LoginFallback() {
  return (
    <div className="relative mx-auto w-full max-w-md">
      <Card className="border-border bg-card/80 shadow-sm backdrop-blur-xl">
        <CardHeader>
          <CardTitle className="text-xl">Sign in</CardTitle>
          <CardDescription>Loading…</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-6 text-muted-foreground">
            <Loader2 className="animate-spin" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useLogin();
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = (values: LoginFormValues) => {
    setFormError(null);
    login.mutate(values, {
      onSuccess: (data) => {
        const redirectTo =
          searchParams.get("redirect") ??
          dashboardPathForRoles(data.user.roles);
        router.replace(redirectTo);
        router.refresh();
      },
      onError: (error: ApiError) => {
        setFormError(error?.message ?? "Unable to sign in. Please try again.");
      },
    });
  };

  return (
    <div className="relative mx-auto w-full max-w-md">
      <Card className="relative overflow-hidden border-border bg-card/80 shadow-[0_1px_0_0_oklch(1_0_0/0.06)_inset,0_24px_60px_-24px_oklch(0.2_0.02_264/0.35)] backdrop-blur-xl">
        {/* hairline brand accent along the top edge */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent"
        />
        <CardHeader>
          <CardTitle className="text-xl">Sign in</CardTitle>
          <CardDescription>
            Enter your credentials to access your account.
          </CardDescription>
        </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <CardContent className="space-y-4">
          {formError ? (
            <div
              role="alert"
              className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
            >
              {formError}
            </div>
          ) : null}

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              aria-invalid={!!errors.email}
              {...register("email")}
            />
            {errors.email ? (
              <p className="text-xs text-destructive">{errors.email.message}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Password</Label>
              <Link
                href={ROUTES.forgotPassword}
                className="text-xs text-muted-foreground underline-offset-4 hover:underline"
              >
                Forgot password?
              </Link>
            </div>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              aria-invalid={!!errors.password}
              {...register("password")}
            />
            {errors.password ? (
              <p className="text-xs text-destructive">
                {errors.password.message}
              </p>
            ) : null}
          </div>
        </CardContent>

        <CardFooter className="flex flex-col gap-4">
          <Button
            type="submit"
            className="w-full transition-all duration-200 hover:brightness-110"
            disabled={login.isPending}
          >
            {login.isPending ? (
              <>
                <Loader2 className="animate-spin" />
                Signing in…
              </>
            ) : (
              "Sign in"
            )}
          </Button>
          <p className="text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link
              href={ROUTES.register}
              className="font-medium text-foreground underline-offset-4 hover:underline"
            >
              Create one
            </Link>
          </p>
        </CardFooter>
        </form>
      </Card>
    </div>
  );
}
