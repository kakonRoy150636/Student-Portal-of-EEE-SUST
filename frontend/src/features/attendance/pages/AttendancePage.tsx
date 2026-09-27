import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { attendanceApi } from '../api/attendanceApi';
import { RollCallGrid } from '../components/RollCallGrid';

export default function AttendancePage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['attendance', 'my-summary'],
    queryFn: async () => (await attendanceApi.getMySummary()).data,
    retry: false,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Academic"
        title="Attendance records"
        description="Measured from recorded class sessions. A missing figure is shown as no data, not zero."
      />
      {isLoading && <PageSkeleton cards={3} rows={2} />}
      {isError && (
        <p className="rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]" role="alert">
          Could not load attendance.
        </p>
      )}
      {!isLoading && !isError && data && data.total_classes === 0 && (
        <EmptyState title="No attendance recorded" description="No class sessions have been recorded for your enrolled courses yet." />
      )}
      {!isLoading && !isError && data && data.total_classes > 0 && <RollCallGrid summary={data} />}
    </div>
  );
}
