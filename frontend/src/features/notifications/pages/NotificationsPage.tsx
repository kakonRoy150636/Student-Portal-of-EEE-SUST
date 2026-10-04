import React from 'react';
import { useNotifications } from '../NotificationContext';
import { NotificationList } from '@/layouts/components/Header';
import { PageHeader } from '@/components/shared/PageHeader';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { NotificationPreferences } from '../components/NotificationPreferences';
import { PwaControls } from '@/components/shared/PwaControls';
import { Button } from '@/components/ui/button';

export default function NotificationsPage() {
  const { items: data, loading: isLoading, error: isError, unread_count, markRead, marking } = useNotifications();

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Tools"
        title="Notifications"
        description="Notices sent to your account. Unread items keep the gold marker."
      />
      <section className="surface max-w-3xl p-2">
        {unread_count > 0 && <Button className="m-2" disabled={marking} onClick={() => markRead()}>Mark all as read ({unread_count})</Button>}
        {isLoading && <PageSkeleton cards={0} rows={3} />}
        {isError && (
          <p className="px-4 py-6 text-center text-sm text-[var(--danger)]" role="alert">
            Could not load notifications.
          </p>
        )}
        {!isLoading && !isError && <NotificationList rows={data ?? []} />}
      </section>
      <NotificationPreferences />
      <PwaControls />
    </div>
  );
}
