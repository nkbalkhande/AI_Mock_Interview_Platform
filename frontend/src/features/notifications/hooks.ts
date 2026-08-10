"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { ApiError } from "@/features/auth/types";

import { listNotifications, markAllNotificationsRead } from "./api";
import type { MarkAllReadResponse, NotificationListResponse } from "./types";

export const notificationKeys = {
  all: ["notifications"] as const,
  list: (unreadOnly: boolean, limit: number) =>
    [...notificationKeys.all, unreadOnly, limit] as const,
};

/**
 * Recent notifications for the current user.
 *
 * Polls every 60s so the bell reflects new admin-driven notifications without
 * needing websockets. Data is cheap (up to 10 rows), so this is fine.
 */
export function useNotifications(params?: {
  unreadOnly?: boolean;
  limit?: number;
  enabled?: boolean;
}) {
  const unreadOnly = params?.unreadOnly ?? false;
  const limit = params?.limit ?? 10;

  return useQuery<NotificationListResponse, ApiError>({
    queryKey: notificationKeys.list(unreadOnly, limit),
    queryFn: () => listNotifications({ unreadOnly, limit }),
    enabled: params?.enabled ?? true,
    refetchInterval: 60_000,
  });
}

/** Mark all unread notifications as read, then refresh the cache. */
export function useMarkAllRead() {
  const qc = useQueryClient();
  return useMutation<MarkAllReadResponse, ApiError>({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
}
