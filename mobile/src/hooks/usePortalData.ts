import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { coursesApi } from '../api/courses';
import { dashboardApi } from '../api/dashboard';
import { notificationsApi } from '../api/notifications';
import { scheduleApi } from '../api/schedule';
import { hasEnrollments } from '../lib/format';
import { useAuth } from './useAuth';

/**
 * Query hooks over the portal API.
 *
 * Everything is gated on `status === 'authenticated'` so a restoring session
 * never fires a burst of 401s, and role-restricted endpoints (enrolments) are
 * skipped for accounts the backend would reject with 403.
 */

const useAuthenticated = (): boolean => useAuth((state) => state.status === 'authenticated');
const useRole = () => useAuth((state) => state.user?.role);

export const queryKeys = {
  dashboard: ['dashboard', 'summary'] as const,
  enrollments: ['course-offerings', 'enrollments', 'me'] as const,
  credits: ['course-offerings', 'enrollments', 'me', 'credits'] as const,
  routine: ['schedules', 'my-routine'] as const,
  notifications: ['notifications', 'summary'] as const,
};

export function useDashboardSummary() {
  const enabled = useAuthenticated();
  return useQuery({
    queryKey: queryKeys.dashboard,
    queryFn: async () => (await dashboardApi.getSummary()).data,
    enabled,
  });
}

export function useMyEnrollments() {
  const authenticated = useAuthenticated();
  const role = useRole();
  const allowed = hasEnrollments(role);

  return useQuery({
    queryKey: queryKeys.enrollments,
    queryFn: async () => (await coursesApi.getMyEnrollments()).data,
    enabled: authenticated && allowed,
  });
}

export function useActiveCredits() {
  const authenticated = useAuthenticated();
  const role = useRole();
  const allowed = hasEnrollments(role);

  return useQuery({
    queryKey: queryKeys.credits,
    queryFn: async () => (await coursesApi.getActiveCredits()).data,
    enabled: authenticated && allowed,
  });
}

export function useMyRoutine() {
  const enabled = useAuthenticated();
  return useQuery({
    queryKey: queryKeys.routine,
    queryFn: async () => (await scheduleApi.getMyRoutine()).data,
    enabled,
  });
}

export function useNotifications() {
  const enabled = useAuthenticated();
  return useQuery({
    queryKey: queryKeys.notifications,
    queryFn: async () => (await notificationsApi.getSummary()).data,
    enabled,
    // The in-app badge is the only live signal on mobile, so poll it while the
    // app is open rather than waiting for a manual refresh.
    refetchInterval: 60_000,
  });
}

export function useMarkNotificationRead() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: number) => notificationsApi.markRead(notificationId),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.notifications });
      // Unread counts also appear on the dashboard tiles.
      void client.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: queryKeys.notifications });
      void client.invalidateQueries({ queryKey: queryKeys.dashboard });
    },
  });
}
