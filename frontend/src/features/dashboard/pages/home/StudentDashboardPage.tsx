import React from 'react';
import { QuickStats } from '../../components/QuickStats';
import { TodayRoutine } from '../../components/TodayRoutine';
import { AttendanceGauge } from '../../components/AttendanceGauge';
import { DashboardHero } from './DashboardHero';
import { useDashboardSummary } from '../../hooks/useDashboardSummary';

export const StudentDashboardPage = () => {
  const { data, isLoading, isError } = useDashboardSummary();
  const s = data?.student;

  return (
    <div className="space-y-6 relative z-10">
      <DashboardHero
        consoleName="01 // STUDENT CONSOLE"
        roleName="STUDENT"
        unreadNotifications={s?.unread_notifications}
      />
      {isError && (
        <div
          className="rounded-xl border p-4 text-sm"
          style={{ borderColor: 'rgba(251,113,133,0.4)', backgroundColor: 'rgba(251,113,133,0.08)', color: '#FB7185' }}
          role="alert"
        >
          Live counters are unavailable right now. The API did not return the
          dashboard summary, so no figures are shown rather than showing stale ones.
        </div>
      )}
      <QuickStats data={s} loading={isLoading} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TodayRoutine routine={s?.routine} loading={isLoading} />
        <AttendanceGauge data={s} loading={isLoading} />
      </div>
    </div>
  );
};
