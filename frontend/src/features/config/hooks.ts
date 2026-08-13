"use client";

import { useQuery } from "@tanstack/react-query";

import type { ApiError } from "@/features/auth/types";

import { getPublicConfig } from "./api";
import { PUBLIC_CONFIG_FALLBACK, type PublicConfig } from "./types";

export const configKeys = {
  public: ["config", "public"] as const,
};

export function usePublicConfig() {
  return useQuery<PublicConfig, ApiError>({
    queryKey: configKeys.public,
    queryFn: getPublicConfig,
    staleTime: 5 * 60_000,
    placeholderData: PUBLIC_CONFIG_FALLBACK,
  });
}
