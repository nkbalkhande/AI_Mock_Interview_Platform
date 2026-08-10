import { apiClient } from "@/lib/api-client";

import type { MarkAllReadResponse, NotificationListResponse } from "./types";

/** GET /notifications — recent notifications for the current user + unread count. */
export async function listNotifications(params?: {
  unreadOnly?: boolean;
  limit?: number;
}): Promise<NotificationListResponse> {
  const { data } = await apiClient.get<NotificationListResponse>(
    "/notifications",
    {
      params: {
        unread_only: params?.unreadOnly ?? false,
        limit: params?.limit ?? 10,
      },
    },
  );
  return data;
}

/** PATCH /notifications/read-all — mark every unread notification as read. */
export async function markAllNotificationsRead(): Promise<MarkAllReadResponse> {
  const { data } = await apiClient.patch<MarkAllReadResponse>(
    "/notifications/read-all",
  );
  return data;
}
