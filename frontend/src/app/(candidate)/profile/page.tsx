"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Camera, Loader2 } from "lucide-react";

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
import { ProfileAvatar } from "@/components/profile/profile-avatar";
import {
  useCandidateProfile,
  useUpdateCandidateProfile,
  useUploadProfilePhoto,
} from "@/features/candidate/hooks";
import {
  candidateProfileSchema,
  type CandidateProfileFormValues,
} from "@/features/candidate/validators";
import { storageFileUrl } from "@/lib/constants";

export default function Page() {
  const { data, isLoading, isError } = useCandidateProfile();
  const updateProfile = useUpdateCandidateProfile();
  const uploadPhoto = useUploadProfilePhoto();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);

  const defaultValues = useMemo(
    () => ({
      fullName: data?.full_name ?? "",
      currentOrganization: data?.current_organization ?? "",
      currentDesignation: data?.current_designation ?? "",
      yearsOfExperience: data?.years_of_experience
        ? Number(data.years_of_experience)
        : 0,
      phoneNumber: data?.phone_number ?? "",
      bio: data?.bio ?? "",
    }),
    [data],
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CandidateProfileFormValues>({
    resolver: zodResolver(candidateProfileSchema),
    defaultValues,
  });

  useEffect(() => {
    if (data) {
      reset(defaultValues);
    }
  }, [data, defaultValues, reset]);

  const profilePhotoUrl = storageFileUrl(data?.profile_photo_path);

  const handlePhotoChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhotoError(null);
    try {
      await uploadPhoto.mutateAsync(file);
    } catch (error) {
      const apiError = error as { message?: string };
      setPhotoError(apiError.message ?? "Failed to upload photo.");
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const onSubmit = async (values: CandidateProfileFormValues) => {
    setFormError(null);

    try {
      await updateProfile.mutateAsync({
        full_name: values.fullName,
        current_organization: values.currentOrganization,
        current_designation: values.currentDesignation,
        years_of_experience: values.yearsOfExperience,
        phone_number: values.phoneNumber || null,
        bio: values.bio || null,
      });
    } catch (error) {
      const apiError = error as { message?: string };
      setFormError(
        apiError.message ?? "Unable to update profile. Please try again.",
      );
    }
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <h1 className="text-xl font-semibold">Loading profile…</h1>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-6">
        <h1 className="text-xl font-semibold">Could not load profile.</h1>
      </div>
    );
  }

  return (
    <div className="p-6 mx-auto max-w-3xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Your profile
          </h1>
          <p className="text-sm text-muted-foreground">
            Keep your candidate profile up to date so interviewers see the most
            accurate information.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button
            type="button"
            className="group relative rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadPhoto.isPending}
          >
            <ProfileAvatar
              fullName={data.full_name}
              photoUrl={profilePhotoUrl}
              className="h-16 w-16"
            />
            <span className="absolute inset-0 flex items-center justify-center rounded-full bg-black/40 opacity-0 transition-opacity group-hover:opacity-100">
              <Camera className="h-5 w-5 text-white" />
            </span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            onChange={handlePhotoChange}
          />
          <div>
            <p className="text-sm text-muted-foreground">Profile photo</p>
            {uploadPhoto.isPending ? (
              <p className="flex items-center gap-1 text-sm text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                Uploading…
              </p>
            ) : (
              <button
                type="button"
                className="text-sm font-medium text-primary hover:underline"
                onClick={() => fileInputRef.current?.click()}
              >
                {profilePhotoUrl ? "Change photo" : "Upload photo"}
              </button>
            )}
            {photoError ? (
              <p className="text-xs text-destructive">{photoError}</p>
            ) : null}
          </div>
        </div>
      </div>

      <Card>
        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <CardHeader>
            <CardTitle className="text-base">Personal details</CardTitle>
            <CardDescription>
              Update the information that will appear in your candidate profile.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            {formError ? (
              <div
                role="alert"
                className="sm:col-span-2 rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {formError}
              </div>
            ) : null}

            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="fullName">Full name</Label>
              <Input
                id="fullName"
                type="text"
                aria-invalid={!!errors.fullName}
                {...register("fullName")}
              />
              {errors.fullName ? (
                <p className="text-xs text-destructive">
                  {errors.fullName.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Label htmlFor="currentOrganization">Current organization</Label>
              <Input
                id="currentOrganization"
                type="text"
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
                step="0.25"
                min="0"
                max="99.99"
                aria-invalid={!!errors.yearsOfExperience}
                {...register("yearsOfExperience", { valueAsNumber: true })}
              />
              {errors.yearsOfExperience ? (
                <p className="text-xs text-destructive">
                  {errors.yearsOfExperience.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="phoneNumber">Phone number</Label>
              <Input
                id="phoneNumber"
                type="tel"
                aria-invalid={!!errors.phoneNumber}
                {...register("phoneNumber")}
              />
              {errors.phoneNumber ? (
                <p className="text-xs text-destructive">
                  {errors.phoneNumber.message}
                </p>
              ) : null}
            </div>

            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="bio">Bio</Label>
              <textarea
                id="bio"
                rows={5}
                className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                aria-invalid={!!errors.bio}
                {...register("bio")}
              />
              {errors.bio ? (
                <p className="text-xs text-destructive">{errors.bio.message}</p>
              ) : null}
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-3">
            <Button type="submit" disabled={isSubmitting || updateProfile.isPending}>
              {isSubmitting || updateProfile.isPending ? (
                <>
                  <Loader2 className="mr-2 inline-block h-4 w-4 animate-spin" />
                  Saving profile…
                </>
              ) : (
                "Save changes"
              )}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
