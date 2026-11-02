import { api } from '../lib/api';
import type { NotificationSummary, PortalNotification } from '../types';

export const notificationsApi = {
  getSummary: () => api.get<NotificationSummary>('/notifications/summary'),

  markRead: (notificationId: number) =>
    api.patch<PortalNotification>(`/notifications/${notificationId}/read`),

  markAllRead: () => api.patch<{ status: string }>('/notifications/read-all'),
};
