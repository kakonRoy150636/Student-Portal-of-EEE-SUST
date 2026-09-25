import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/axios';
import { NotificationList } from '@/layouts/components/Header';

/**
 * Destination for the header bell. The bell used to be a button with no
 * handler, so this route gives it somewhere real to go.
 */
export default function NotificationsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => (await api.get('/notifications')).data,
    retry: false,
  });

  return (
    <div className="space-y-6 relative z-10">
      <h1 className="text-2xl font-bold tracking-tight text-white font-mono uppercase">
        Notifications
      </h1>
      <section className="hud-box corner-brackets rounded-xl p-2 max-w-3xl">
        {isLoading && <div className="h-16 m-2 animate-pulse rounded bg-slate-900/60" aria-hidden="true" />}
        {isError && (
          <p className="px-4 py-6 text-center text-xs font-mono" style={{ color: '#FB7185' }} role="alert">
            Could not load notifications.
          </p>
        )}
        {!isLoading && !isError && <NotificationList rows={data ?? []} />}
      </section>
    </div>
  );
}
