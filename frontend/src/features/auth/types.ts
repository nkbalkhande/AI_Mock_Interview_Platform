import type { Role } from "@/lib/constants";

export interface LoginInput {
  email: string;
  password: string;
}

export interface RegisterInput {
  full_name: string;
  email: string;
  password: string;
  current_organization: string;
  current_designation: string;
  years_of_experience: number;
  phone_number?: string;
  /** Required resume file (pdf/doc/docx/txt). */
  resume: File;
  /** Optional profile photo (png/jpeg/webp). */
  profile_photo?: File;
}

/** Authenticated user identity returned by the backend login endpoint. */
export interface AuthUser {
  id: string;
  full_name: string;
  email: string;
  roles: Role[];
  profile_photo_path: string | null;
}

export interface LoginResponse {
  user: AuthUser;
}

export interface SendEmailOtpResponse {
  success: boolean;
  message: string;
  cooldown_seconds: number;
}

export interface VerifyEmailResponse {
  success: boolean;
  verified: boolean;
  message: string;
}

/** Normalized error shape produced by the axios response interceptor. */
export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
