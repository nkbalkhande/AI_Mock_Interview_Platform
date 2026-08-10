import { z } from "zod";

export const assignInterviewSchema = z
  .object({
    candidate_id: z.string().uuid("Select a valid candidate."),
    job_role_id: z.string().uuid().nullish(),
    role_name: z.string().min(1, "Role name is required.").max(150),
    job_description: z.string().min(1, "Job description is required."),
    role_requirements: z.string().nullish(),
    required_experience_min: z.coerce.number().min(0).nullish(),
    required_experience_max: z.coerce.number().min(0).nullish(),
    scheduled_at: z.string().min(1, "Schedule date/time is required."),
    timezone: z.string().default("UTC"),
    duration_minutes: z.coerce.number().int().min(1).max(180).default(30),
    instructions: z.string().nullish(),
  })
  .refine(
    (d) =>
      d.required_experience_min == null ||
      d.required_experience_max == null ||
      d.required_experience_max >= d.required_experience_min,
    {
      message: "Max experience must be >= min experience.",
      path: ["required_experience_max"],
    },
  );

export type AssignInterviewFormData = z.infer<typeof assignInterviewSchema>;

export const submitDecisionSchema = z.object({
  admin_decision: z.enum(["CLEARED", "NOT_CLEARED", "NEEDS_FURTHER_REVIEW"], {
    required_error: "Please select a decision.",
  }),
  admin_feedback: z.string().nullish(),
});

export type SubmitDecisionFormData = z.infer<typeof submitDecisionSchema>;
