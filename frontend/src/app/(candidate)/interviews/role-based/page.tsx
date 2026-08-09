"use client";

import { useMemo, useState } from "react";
import { ArrowRight, Briefcase, Loader2, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  useJobRoles,
  useStartRolePractice,
} from "@/features/interviews/hooks";
import { ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

const DURATIONS = [15, 30, 45, 60];
const MAX_REQUIREMENTS = 20;
const MAX_REQUIREMENT_LENGTH = 300;
const MAX_SKILLS = 30;
const MAX_SKILL_LENGTH = 100;

export default function RoleBasedInterviewPage() {
  const router = useRouter();
  const roles = useJobRoles();
  const start = useStartRolePractice();
  const [selection, setSelection] = useState<string | null>(null);
  const [duration, setDuration] = useState(30);
  const [customName, setCustomName] = useState("");
  const [customRequirements, setCustomRequirements] = useState("");
  const [customSkills, setCustomSkills] = useState("");
  const isCustom = selection === "custom";
  const selectedRole = useMemo(
    () => roles.data?.find((role) => role.id === selection),
    [roles.data, selection],
  );
  const requirements = customRequirements
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  const skills = customSkills
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const catalogReady = Boolean(roles.data?.length);
  const customInputValid =
    customName.trim().length >= 2 &&
    requirements.length > 0 &&
    requirements.length <= MAX_REQUIREMENTS &&
    requirements.every((item) => item.length <= MAX_REQUIREMENT_LENGTH) &&
    skills.length <= MAX_SKILLS &&
    skills.every((item) => item.length <= MAX_SKILL_LENGTH);
  const canStart =
    catalogReady && (isCustom ? customInputValid : Boolean(selectedRole));

  async function handleStart() {
    if (!canStart) return;
    const result = await start.mutateAsync(
      isCustom
        ? {
            custom_role_name: customName.trim(),
            custom_requirements: requirements,
            custom_skills: skills,
            duration_minutes: duration,
          }
        : { job_role_id: selectedRole!.id, duration_minutes: duration },
    );
    router.push(ROUTES.candidate.interview(result.session_id));
  }

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header>
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-lg bg-primary text-primary-foreground">
            <Briefcase className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-2xl font-semibold">Role-Based Practice</h1>
            <p className="text-sm text-muted-foreground">
              Choose a role from the live catalog or define your own.
            </p>
          </div>
        </div>
      </header>

      {roles.isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div
              key={item}
              className="h-40 animate-pulse rounded-xl border bg-muted/40"
            />
          ))}
        </div>
      ) : roles.isError ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <p className="text-sm text-destructive">
              Could not load the role catalog. Starting is disabled.
            </p>
            <Button variant="outline" onClick={() => roles.refetch()}>
              <RefreshCw className="mr-2 h-4 w-4" /> Retry
            </Button>
          </CardContent>
        </Card>
      ) : roles.data?.length ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {roles.data?.map((role) => (
            <button
              key={role.id}
              type="button"
              onClick={() => setSelection(role.id)}
              className={cn(
                "rounded-xl border bg-card p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                selection === role.id
                  ? "border-primary bg-primary/5"
                  : "hover:border-primary/40",
              )}
            >
              <h2 className="font-semibold">{role.name}</h2>
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                {role.description || "Role-focused adaptive interview"}
              </p>
              <div className="mt-3 flex flex-wrap gap-1">
                {role.skills.slice(0, 4).map((skill) => (
                  <span
                    key={skill}
                    className="rounded-full bg-muted px-2 py-0.5 text-xs"
                  >
                    {skill}
                  </span>
                ))}
              </div>
              <p className="mt-3 text-xs text-muted-foreground">
                Experience: {formatExperience(role.experience_min, role.experience_max)}
              </p>
            </button>
          ))}
          <button
            type="button"
            onClick={() => setSelection("custom")}
            className={cn(
              "rounded-xl border border-dashed bg-card p-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              isCustom ? "border-primary bg-primary/5" : "hover:border-primary/40",
            )}
          >
            <h2 className="font-semibold">Other / Custom role</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Define a role and the requirements you want assessed.
            </p>
          </button>
        </div>
      ) : (
        <p className="rounded-lg border p-4 text-sm text-muted-foreground">
          No catalog roles are active. Starting an interview is disabled until
          the catalog is available.
        </p>
      )}

      {selectedRole ? (
        <Card>
          <CardHeader>
            <h2 className="font-semibold">{selectedRole.name} focus</h2>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <DetailList title="Requirements" items={selectedRole.requirements} />
            <DetailList title="Skills" items={selectedRole.skills} />
          </CardContent>
        </Card>
      ) : null}

      {isCustom ? (
        <Card>
          <CardHeader>
            <h2 className="font-semibold">Custom role details</h2>
          </CardHeader>
          <CardContent className="grid gap-4">
            <label className="grid gap-1 text-sm font-medium">
              Role name
              <input
                value={customName}
                onChange={(event) => setCustomName(event.target.value)}
                className="rounded-md border bg-transparent px-3 py-2 font-normal"
                placeholder="e.g. Platform Engineer"
                maxLength={150}
              />
            </label>
            <label className="grid gap-1 text-sm font-medium">
              Requirements (one per line)
              <textarea
                value={customRequirements}
                onChange={(event) => setCustomRequirements(event.target.value)}
                className="min-h-28 rounded-md border bg-transparent px-3 py-2 font-normal"
                placeholder={"Design reliable distributed systems\nOperate cloud infrastructure"}
                maxLength={MAX_REQUIREMENTS * (MAX_REQUIREMENT_LENGTH + 1)}
              />
              <span className="text-xs font-normal text-muted-foreground">
                Up to {MAX_REQUIREMENTS} items, {MAX_REQUIREMENT_LENGTH} characters each.
              </span>
            </label>
            <label className="grid gap-1 text-sm font-medium">
              Skills (comma separated)
              <input
                value={customSkills}
                onChange={(event) => setCustomSkills(event.target.value)}
                className="rounded-md border bg-transparent px-3 py-2 font-normal"
                placeholder="Python, Kubernetes, System Design"
                maxLength={MAX_SKILLS * (MAX_SKILL_LENGTH + 1)}
              />
              <span className="text-xs font-normal text-muted-foreground">
                Up to {MAX_SKILLS} items, {MAX_SKILL_LENGTH} characters each.
              </span>
            </label>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardContent className="flex flex-col gap-5 pt-6">
          <div>
            <h2 className="text-sm font-semibold">Interview duration</h2>
            <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {DURATIONS.map((minutes) => (
                <button
                  key={minutes}
                  type="button"
                  onClick={() => setDuration(minutes)}
                  className={cn(
                    "rounded-lg border px-3 py-2 text-sm",
                    duration === minutes && "border-primary bg-primary/5",
                  )}
                >
                  {minutes} minutes
                </button>
              ))}
            </div>
          </div>
          {start.isError ? (
            <p className="text-sm text-destructive">
              {start.error.message || "Could not start the interview."}
            </p>
          ) : null}
          <Button
            className="self-stretch sm:self-end"
            disabled={
              !canStart ||
              roles.isLoading ||
              roles.isError ||
              !roles.data?.length ||
              start.isPending
            }
            onClick={handleStart}
          >
            {start.isPending ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Preparing interview…</>
            ) : (
              <>Start interview <ArrowRight className="ml-2 h-4 w-4" /></>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function DetailList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h3 className="text-sm font-medium">{title}</h3>
      {items.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          {items.map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">Not specified</p>
      )}
    </div>
  );
}

function formatExperience(minimum: number | null, maximum: number | null) {
  if (minimum == null && maximum == null) return "Not specified";
  if (maximum == null) return `${minimum}+ years`;
  return `${minimum ?? 0}–${maximum} years`;
}