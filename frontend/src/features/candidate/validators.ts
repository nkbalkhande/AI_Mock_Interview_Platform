import { z } from "zod";

export const candidateProfileSchema = z.object({
  fullName: z
    .string()
    .trim()
    .min(2, "Enter your full name")
    .max(150, "Name is too long"),
  currentOrganization: z
    .string()
    .trim()
    .min(1, "Current organization is required")
    .max(200, "Organization is too long"),
  currentDesignation: z
    .string()
    .trim()
    .min(1, "Designation is required")
    .max(150, "Designation is too long"),
  yearsOfExperience: z.coerce
    .number({ invalid_type_error: "Enter your years of experience" })
    .min(0, "Experience cannot be negative")
    .max(99.99, "Enter a realistic value"),
  phoneNumber: z
    .string()
    .trim()
    .max(30, "Phone number is too long")
    .optional()
    .or(z.literal("")),
  bio: z
    .string()
    .trim()
    .max(1000, "Bio is too long")
    .optional()
    .or(z.literal("")),
});

export type CandidateProfileFormValues = z.infer<typeof candidateProfileSchema>;
