"use client";

import { create } from "zustand";

import type { SessionUser } from "@/lib/auth";

/**
 * Client-side auth state. Tokens live in httpOnly cookies (never touched by JS);
 * this store only holds the current user's identity so the UI can render role
 * aware navigation without re-fetching on every route.
 */
interface AuthState {
  user: SessionUser | null;
  setUser: (user: SessionUser | null) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  clear: () => set({ user: null }),
}));

/** Convenience hook exposing the current session user. */
export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const clear = useAuthStore((s) => s.clear);
  return { user, setUser, clear, isAuthenticated: user !== null };
}
