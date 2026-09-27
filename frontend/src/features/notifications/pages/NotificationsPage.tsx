import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { NotificationList } from '@/layouts/components/Header';
import { PageHeader } from '@/components/shared/PageHeader';
import { PageSkeleton } from '@/components/shared/PageSkeleton';

export default function NotificationsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => (await api.get('/notifications')).data,
    retry: false,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Tools"
        title="Notifications"
        description="Notices sent to your account. Unread items keep the gold marker."
      />
      <section className="surface max-w-3xl p-2">
        {isLoading && <PageSkeleton cards={0} rows={3} />}
        {isError && (
          <p className="px-4 py-6 text-center text-sm text-[var(--danger)]" role="alert">
            Could not load notifications.
          </p>
        )}
        {!isLoading && !isError && <NotificationList rows={data ?? []} />}
      </section>
    </div>
  );
}
