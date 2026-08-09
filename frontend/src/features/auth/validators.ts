import { z } from "zod";

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, "Email is required")
    .email("Enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    fullName: z
      .string()
      .trim()
      .min(2, "Enter your full name")
      .max(150, "Name is too long"),
    email: z
      .string()
      .min(1, "Email is required")
      .email("Enter a valid email address"),
    password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .max(128, "Password is too long"),
    confirmPassword: z.string().min(1, "Please confirm your password"),
    currentOrganization: z
      .string()
      .trim()
      .min(1, "Current organization is required")
      .max(200, "Organization name is too long"),
    currentDesignation: z
      .string()
      .trim()
      .min(1, "Current designation is required")
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
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

export type RegisterFormValues = z.infer<typeof registerSchema>;
