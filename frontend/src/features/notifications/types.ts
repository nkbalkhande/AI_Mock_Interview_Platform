export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
  reference_type: string | null;
  reference_id: string | null;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  unread_count: number;
}
