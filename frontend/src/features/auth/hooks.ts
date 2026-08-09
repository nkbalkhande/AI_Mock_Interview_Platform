"use client";

import { useMutation } from "@tanstack/react-query";

import { useAuthStore } from "@/hooks/use-auth";

import { login, register } from "./api";
import type {
  ApiError,
  LoginInput,
  LoginResponse,
  RegisterInput,
} from "./types";

/**
 * Mutation wrapper around the login call. On success it hydrates the client-side
 * auth store with the returned user so the rest of the app knows who is signed
 * in. The error type is the normalized envelope from the axios interceptor.
 */
export function useLogin() {
  const setUser = useAuthStore((s) => s.setUser);

  return useMutation<LoginResponse, ApiError, LoginInput>({
    mutationFn: login,
    onSuccess: ({ user }) => {
      setUser({
        id: user.id,
        fullName: user.full_name,
        email: user.email,
        roles: user.roles,
      });
    },
  });
}

/**
 * Mutation wrapper around the register call. Signup logs the user straight in
 * (cookies are set by the backend), so we hydrate the auth store just like login.
 */
export function useRegister() {
  const setUser = useAuthStore((s) => s.setUser);

  return useMutation<LoginResponse, ApiError, RegisterInput>({
    mutationFn: register,
    onSuccess: ({ user }) => {
      setUser({
        id: user.id,
        fullName: user.full_name,
        email: user.email,
        roles: user.roles,
      });
    },
  });
}
