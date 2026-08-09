import { apiClient } from "@/lib/api-client";

import type { NotificationListResponse } from "./types";

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
