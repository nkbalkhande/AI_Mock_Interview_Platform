import { apiClient } from "@/lib/api-client";

import type { AuthUser, LoginInput, LoginResponse, RegisterInput } from "./types";

/**
 * POST /auth/login — verifies credentials. On success the backend sets httpOnly
 * auth cookies and returns the user's identity. `withCredentials` (configured on
 * apiClient) ensures the Set-Cookie is stored and sent on subsequent requests.
 */
export async function login(input: LoginInput): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>("/auth/login", input);
  return data;
}

/**
 * POST /auth/register — creates an account (with resume upload) and logs the
 * user in. Sent as multipart/form-data because it includes files; we leave the
 * Content-Type unset so the browser adds the correct multipart boundary.
 */
export async function register(input: RegisterInput): Promise<LoginResponse> {
  const form = new FormData();
  form.append("full_name", input.full_name);
  form.append("email", input.email);
  form.append("password", input.password);
  form.append("current_organization", input.current_organization);
  form.append("current_designation", input.current_designation);
  form.append("years_of_experience", String(input.years_of_experience));
  if (input.phone_number) {
    form.append("phone_number", input.phone_number);
  }
  form.append("resume", input.resume);
  if (input.profile_photo) {
    form.append("profile_photo", input.profile_photo);
  }

  const { data } = await apiClient.post<LoginResponse>("/auth/register", form, {
    headers: { "Content-Type": undefined },
  });
  return data;
}

/**
 * GET /auth/me — resolve the current user from the httpOnly session cookie.
 *
 * Used on app boot / page refresh to rehydrate the client auth store; JS
 * can't read the cookie itself, so we ask the backend who we are.
 */
export async function getMe(): Promise<AuthUser> {
  const { data } = await apiClient.get<AuthUser>("/auth/me");
  return data;
}

/**
 * POST /auth/logout — clear auth cookies. Idempotent; returns 204 on success.
 * The API returns no body, so we don't try to parse one.
 */
export async function logout(): Promise<void> {
  await apiClient.post("/auth/logout");
}
