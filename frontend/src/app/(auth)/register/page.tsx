"use client";

import { useState, type ChangeEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
import { EmailVerificationField } from "@/features/auth/email-verification-field";
import { useRegister } from "@/features/auth/hooks";
import type { ApiError } from "@/features/auth/types";
import {
  registerSchema,
  type RegisterFormValues,
} from "@/features/auth/validators";
import { ROUTES } from "@/lib/constants";

const MAX_UPLOAD_MB = 10;
const RESUME_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
];
const PHOTO_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/webp"];

function validateFile(
  file: File,
  allowed: string[],
  label: string,
): string | null {
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
    return `${label} must be smaller than ${MAX_UPLOAD_MB}MB`;
  }
  if (allowed.length && !allowed.includes(file.type)) {
    return `Unsupported ${label.toLowerCase()} format`;
  }
  return null;
}

export default function RegisterPage() {
  const router = useRouter();
  const registerUser = useRegister();
  const [formError, setFormError] = useState<string | null>(null);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [emailVerified, setEmailVerified] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: "",
      email: "",
      password: "",
      confirmPassword: "",
      currentOrganization: "",
      currentDesignation: "",
      yearsOfExperience: 0,
      phoneNumber: "",
    },
  });

  const onResumeChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setResumeFile(file);
    setResumeError(file ? validateFile(file, RESUME_TYPES, "Resume") : null);
  };

  const onPhotoChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setPhotoFile(file);
    setPhotoError(file ? validateFile(file, PHOTO_TYPES, "Photo") : null);
  };

  const emailValue = watch("email");

  const onSubmit = (values: RegisterFormValues) => {
    setFormError(null);

    if (!emailVerified) {
      setFormError(
        "Please verify your email address before completing registration.",
      );
      return;
    }

    if (!resumeFile) {
      setResumeError("Please upload your resume");
      return;
    }
    const resumeIssue = validateFile(resumeFile, RESUME_TYPES, "Resume");
    if (resumeIssue) {
      setResumeError(resumeIssue);
      return;
    }
    if (photoFile) {
      const photoIssue = validateFile(photoFile, PHOTO_TYPES, "Photo");
      if (photoIssue) {
        setPhotoError(photoIssue);
        return;
      }
    }

    registerUser.mutate(
      {
        full_name: values.fullName,
        email: values.email,
        password: values.password,
        current_organization: values.currentOrganization,
        current_designation: values.currentDesignation,
        years_of_experience: values.yearsOfExperience,
        phone_number: values.phoneNumber || undefined,
        resume: resumeFile,
        profile_photo: photoFile ?? undefined,
      },
      {
        onSuccess: () => {
          router.replace(ROUTES.candidate.dashboard);
          router.refresh();
        },
        onError: (error: ApiError) => {
          setFormError(
            error?.message ?? "Unable to create your account. Please try again.",
          );
        },
      },
    );
  };

  return (
    <div className="relative mx-auto w-full max-w-3xl">
      <Card className="relative overflow-hidden border-border bg-card/80 shadow-[0_1px_0_0_oklch(1_0_0/0.06)_inset,0_24px_60px_-24px_oklch(0.2_0.02_264/0.35)] backdrop-blur-xl">
        {/* hairline brand accent along the top edge */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/60 to-transparent"
        />
        <CardHeader>
          <CardTitle className="text-xl">Create your account</CardTitle>
          <CardDescription>
            Tell us about yourself and upload your resume to get started.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {formError ? (
              <div
                role="alert"
                className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive sm:col-span-2"
              >
                {formError}
              </div>
            ) : null}

            <div className="space-y-2">
              <Label htmlFor="fullName">Full name</Label>
              <Input
                id="fullName"
                type="text"
                autoComplete="name"
                placeholder="Ada Lovelace"
                aria-invalid={!!errors.fullName}
                {...register("fullName")}
              />
              {errors.fullName ? (
                <p className="text-xs text-destructive">
                  {errors.fullName.message}
                </p>
              ) : null}
            </div>

            <EmailVerificationField
              email={emailValue}
              emailError={errors.email?.message}
              registerEmail={register("email")}
              verified={emailVerified}
              onVerifiedChange={setEmailVerified}
            />

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                placeholder="Min 8 characters"
                aria-invalid={!!errors.password}
                {...register("password")}
              />
              {errors.password ? (
                <p className="text-xs text-destructive">
                  {errors.password.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm password</Label>
              <Input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                placeholder="Re-enter password"
                aria-invalid={!!errors.confirmPassword}
                {...register("confirmPassword")}
              />
              {errors.confirmPassword ? (
                <p className="text-xs text-destructive">
                  {errors.confirmPassword.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="currentOrganization">Current organization</Label>
              <Input
                id="currentOrganization"
                type="text"
                autoComplete="organization"
                placeholder="Acme Corp"
                aria-invalid={!!errors.currentOrganization}
                {...register("currentOrganization")}
              />
              {errors.currentOrganization ? (
                <p className="text-xs text-destructive">
                  {errors.currentOrganization.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="currentDesignation">Designation</Label>
              <Input
                id="currentDesignation"
                type="text"
                autoComplete="organization-title"
                placeholder="Data Scientist"
                aria-invalid={!!errors.currentDesignation}
                {...register("currentDesignation")}
              />
              {errors.currentDesignation ? (
                <p className="text-xs text-destructive">
                  {errors.currentDesignation.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="yearsOfExperience">Years of experience</Label>
              <Input
                id="yearsOfExperience"
                type="number"
                step="0.5"
                min="0"
                max="99.99"
                placeholder="2.5"
                aria-invalid={!!errors.yearsOfExperience}
                {...register("yearsOfExperience")}
              />
              {errors.yearsOfExperience ? (
                <p className="text-xs text-destructive">
                  {errors.yearsOfExperience.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="phoneNumber">
                Phone number{" "}
                <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input
                id="phoneNumber"
                type="tel"
                autoComplete="tel"
                placeholder="+91 98765 43210"
                aria-invalid={!!errors.phoneNumber}
                {...register("phoneNumber")}
              />
              {errors.phoneNumber ? (
                <p className="text-xs text-destructive">
                  {errors.phoneNumber.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="resume">Resume</Label>
              <Input
                id="resume"
                type="file"
                accept=".pdf,.doc,.docx,.txt"
                onChange={onResumeChange}
                aria-invalid={!!resumeError}
                className="cursor-pointer file:mr-3 file:cursor-pointer file:rounded file:border-0 file:bg-secondary file:px-2 file:py-1 file:text-xs file:font-medium"
              />
              <p className="text-xs text-muted-foreground">
                PDF, DOC, DOCX, or TXT — up to {MAX_UPLOAD_MB}MB.
              </p>
              {resumeError ? (
                <p className="text-xs text-destructive">{resumeError}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="profilePhoto">
                Profile photo{" "}
                <span className="text-muted-foreground">(optional)</span>
              </Label>
              <Input
                id="profilePhoto"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={onPhotoChange}
                aria-invalid={!!photoError}
                className="cursor-pointer file:mr-3 file:cursor-pointer file:rounded file:border-0 file:bg-secondary file:px-2 file:py-1 file:text-xs file:font-medium"
              />
              {photoError ? (
                <p className="text-xs text-destructive">{photoError}</p>
              ) : null}
            </div>
          </CardContent>

          <CardFooter className="flex flex-col gap-4">
            <Button
              type="submit"
              className="w-full transition-all duration-200 hover:brightness-110"
              disabled={registerUser.isPending}
            >
              {registerUser.isPending ? (
                <>
                  <Loader2 className="animate-spin" />
                  Creating account…
                </>
              ) : (
                "Create account"
              )}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              Already have an account?{" "}
              <Link
                href={ROUTES.login}
                className="font-medium text-foreground underline-offset-4 hover:underline"
              >
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
