"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, CheckCircle2, Loader2 } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  useAssignInterview,
  useJobRoles,
  useUsers,
} from "@/features/admin/hooks";
import {
  assignInterviewSchema,
  type AssignInterviewFormData,
} from "@/features/admin/validators";
import { ROUTES } from "@/lib/constants";

export default function AssignInterviewPage() {
  const router = useRouter();
  const [success, setSuccess] = useState<string | null>(null);

  const { data: usersData } = useUsers({
    page_size: 100,
    role: "CANDIDATE",
    is_active: true,
  });
  const { data: jobRoles } = useJobRoles();
  const assign = useAssignInterview();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<AssignInterviewFormData>({
    resolver: zodResolver(assignInterviewSchema),
    defaultValues: {
      timezone: "UTC",
      duration_minutes: 30,
    },
  });

  const selectedRoleId = watch("job_role_id");

  function onJobRoleChange(roleId: string) {
    const role = jobRoles?.find((r) => r.id === roleId);
    if (role) {
      setValue("job_role_id", role.id);
      setValue("role_name", role.name);
      if (role.description) {
        setValue("role_requirements", role.description);
      }
      if (role.experience_min) {
        setValue(
          "required_experience_min",
          Number(role.experience_min),
        );
      }
      if (role.experience_max) {
        setValue(
          "required_experience_max",
          Number(role.experience_max),
        );
      }
    }
  }

  async function onSubmit(data: AssignInterviewFormData) {
    try {
      const result = await assign.mutateAsync({
        candidate_id: data.candidate_id,
        job_role_id: data.job_role_id ?? undefined,
        role_name: data.role_name,
        job_description: data.job_description,
        role_requirements: data.role_requirements ?? undefined,
        required_experience_min: data.required_experience_min ?? undefined,
        required_experience_max: data.required_experience_max ?? undefined,
        scheduled_at: new Date(data.scheduled_at).toISOString(),
        timezone: data.timezone,
        duration_minutes: data.duration_minutes,
        instructions: data.instructions ?? undefined,
      });
      setSuccess(result.message);
      setTimeout(() => router.push(ROUTES.admin.interviews), 2000);
    } catch {
      // error handled by mutation state
    }
  }

  if (success) {
    return (
      <div className="mx-auto flex w-full max-w-2xl flex-col items-center gap-4 py-20">
        <CheckCircle2 className="h-12 w-12 text-emerald-500" />
        <p className="text-lg font-semibold">{success}</p>
        <p className="text-sm text-muted-foreground">
          Redirecting to interviews...
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href={ROUTES.admin.interviews}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Assign Interview
          </h1>
          <p className="text-sm text-muted-foreground">
            Schedule an interview for a candidate.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Candidate & Role</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div>
              <Label htmlFor="candidate_id">Candidate</Label>
              <select
                id="candidate_id"
                {...register("candidate_id")}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">Select a candidate...</option>
                {usersData?.items.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.email})
                  </option>
                ))}
              </select>
              {errors.candidate_id ? (
                <p className="mt-1 text-xs text-destructive">
                  {errors.candidate_id.message}
                </p>
              ) : null}
            </div>

            <div>
              <Label>Job Role (optional — pre-fills fields)</Label>
              <select
                value={selectedRoleId ?? ""}
                onChange={(e) => onJobRoleChange(e.target.value)}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">Select a job role...</option>
                {jobRoles?.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <Label htmlFor="role_name">Role Name</Label>
              <Input
                id="role_name"
                {...register("role_name")}
                placeholder="e.g. AI Engineer"
                className="mt-1"
              />
              {errors.role_name ? (
                <p className="mt-1 text-xs text-destructive">
                  {errors.role_name.message}
                </p>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Job Description</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div>
              <Label htmlFor="job_description">Job Description</Label>
              <textarea
                id="job_description"
                {...register("job_description")}
                rows={6}
                placeholder="Paste the full job description..."
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
              {errors.job_description ? (
                <p className="mt-1 text-xs text-destructive">
                  {errors.job_description.message}
                </p>
              ) : null}
            </div>

            <div>
              <Label htmlFor="role_requirements">
                Role Requirements (optional)
              </Label>
              <textarea
                id="role_requirements"
                {...register("role_requirements")}
                rows={3}
                placeholder="Key requirements or skills..."
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="required_experience_min">
                  Min Experience (yrs)
                </Label>
                <Input
                  id="required_experience_min"
                  type="number"
                  step="0.5"
                  {...register("required_experience_min")}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="required_experience_max">
                  Max Experience (yrs)
                </Label>
                <Input
                  id="required_experience_max"
                  type="number"
                  step="0.5"
                  {...register("required_experience_max")}
                  className="mt-1"
                />
                {errors.required_experience_max ? (
                  <p className="mt-1 text-xs text-destructive">
                    {errors.required_experience_max.message}
                  </p>
                ) : null}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Schedule</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="scheduled_at">Date & Time</Label>
                <Input
                  id="scheduled_at"
                  type="datetime-local"
                  {...register("scheduled_at")}
                  className="mt-1"
                />
                {errors.scheduled_at ? (
                  <p className="mt-1 text-xs text-destructive">
                    {errors.scheduled_at.message}
                  </p>
                ) : null}
              </div>
              <div>
                <Label htmlFor="timezone">Timezone</Label>
                <Input
                  id="timezone"
                  {...register("timezone")}
                  className="mt-1"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="duration_minutes">Duration (minutes)</Label>
              <Input
                id="duration_minutes"
                type="number"
                {...register("duration_minutes")}
                className="mt-1"
              />
              {errors.duration_minutes ? (
                <p className="mt-1 text-xs text-destructive">
                  {errors.duration_minutes.message}
                </p>
              ) : null}
            </div>

            <div>
              <Label htmlFor="instructions">
                Instructions for candidate (optional)
              </Label>
              <textarea
                id="instructions"
                {...register("instructions")}
                rows={3}
                placeholder="Any special instructions..."
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              />
            </div>
          </CardContent>
        </Card>

        {assign.isError ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            {(assign.error as { message?: string })?.message ??
              "Failed to assign interview."}
          </div>
        ) : null}

        <Button type="submit" disabled={assign.isPending} className="w-full">
          {assign.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : null}
          Assign Interview
        </Button>
      </form>
    </div>
  );
}
