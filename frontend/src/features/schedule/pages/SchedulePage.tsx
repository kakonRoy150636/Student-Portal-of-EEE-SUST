import React, { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { scheduleApi } from '../api/scheduleApi';
import { ScheduleCalendar } from '../components/ScheduleCalendar';
import { useAuth } from '@/contexts/AuthContext';
import { saveRoutine } from '@/lib/offlineRoutine';

export default function SchedulePage() {
  const { user } = useAuth();
  const { data, isLoading, isError } = useQuery({
    queryKey: ['schedules', 'my-routine', user?.id],
    queryFn: async () => (await scheduleApi.getMyRoutine()).data,
    retry: false,
  });
  useEffect(() => {
    if (user && data) void saveRoutine(user.id, data).catch(() => {});
  }, [user, data]);

  const classes = useMemo(() => data ?? [], [data]);
  const days = useMemo(() => {
    const unique = Array.from(new Set(classes.map((item) => item.day_of_week)));
    return unique.length ? unique : ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday'];
  }, [classes]);

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Academic"
        title="Class routine"
        description="Your published weekly timetable. Empty days mean no class is listed for that day."
      />
      <p className="text-sm text-[var(--text-muted)]">This routine is saved on your device for offline viewing. Signing out clears the saved copy.</p>
      {isLoading && <PageSkeleton cards={0} rows={4} />}
      {isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load the class routine. <a className="underline" href="/offline.html">View saved offline routine</a>
        </p>
      )}
      {!isLoading && !isError && classes.length === 0 && (
        <EmptyState title="No classes published" description="Your enrolled courses do not have a published timetable yet." />
      )}
      {!isLoading && !isError && classes.length > 0 && <ScheduleCalendar days={days} classes={classes} />}
    </div>
  );
}
