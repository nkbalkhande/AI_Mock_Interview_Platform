"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { useAuthStore } from "@/hooks/use-auth";
import { ROUTES } from "@/lib/constants";

import { getMe, login, logout, register } from "./api";
import type {
  ApiError,
  AuthUser,
  LoginInput,
  LoginResponse,
  RegisterInput,
} from "./types";

const AUTH_ME_KEY = ["auth", "me"] as const;

/**
 * Mutation wrapper around the login call. On success it hydrates the client-side
 * auth store with the returned user so the rest of the app knows who is signed
 * in. The error type is the normalized envelope from the axios interceptor.
 */
export function useLogin() {
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();

  return useMutation<LoginResponse, ApiError, LoginInput>({
    mutationFn: login,
    onSuccess: ({ user }) => {
      setUser({
        id: user.id,
        fullName: user.full_name,
        email: user.email,
        roles: user.roles,
        profilePhotoPath: user.profile_photo_path,
      });
      queryClient.setQueryData(AUTH_ME_KEY, () => user);
    },
  });
}

/**
 * Mutation wrapper around the register call. Signup logs the user straight in
 * (cookies are set by the backend), so we hydrate the auth store just like login.
 */
export function useRegister() {
  const setUser = useAuthStore((s) => s.setUser);
  const queryClient = useQueryClient();

  return useMutation<LoginResponse, ApiError, RegisterInput>({
    mutationFn: register,
    onSuccess: ({ user }) => {
      setUser({
        id: user.id,
        fullName: user.full_name,
        email: user.email,
        roles: user.roles,
        profilePhotoPath: user.profile_photo_path,
      });
      queryClient.setQueryData(AUTH_ME_KEY, () => user);
    },
  });
}

/**
 * Bootstrap query for the current session.
 *
 * The dashboard layout mounts this on every candidate route so the client
 * auth store is populated from the httpOnly cookie on refresh. On failure
 * (typically 401) the query silently resolves to ``null`` — the middleware
 * has already redirected unauthenticated users to /login before this ever
 * runs, so a hard error here would be double-signalling.
 */
export function useMe(options?: { enabled?: boolean }) {
  const setUser = useAuthStore((s) => s.setUser);

  return useQuery<AuthUser | null, ApiError>({
    queryKey: [...AUTH_ME_KEY],
    enabled: options?.enabled ?? true,
    // Session identity is stable across a browser session; skip the auto refetch.
    staleTime: 5 * 60 * 1000,
    retry: false,
    queryFn: async () => {
      try {
        const me = await getMe();
        setUser({
          id: me.id,
          fullName: me.full_name,
          email: me.email,
          roles: me.roles,
          profilePhotoPath: me.profile_photo_path,
        });
        return me;
      } catch (err) {
        // 401 = no valid session. Middleware will already have sent the user
        // to /login on a protected page; here we just report "no user".
        const apiError = err as ApiError;
        if (apiError?.code === "authentication_error") {
          setUser(null);
          return null;
        }
        throw err;
      }
    },
  });
}

/**
 * Sign the user out: clear cookies server-side, wipe client cache + store,
 * then push to /login. Used by the profile dropdown.
 */
export function useLogout() {
  const clear = useAuthStore((s) => s.clear);
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation<void, ApiError, void>({
    mutationFn: logout,
    onSettled: () => {
      clear();
      queryClient.clear();
      router.replace(ROUTES.login);
      router.refresh();
    },
  });
}
