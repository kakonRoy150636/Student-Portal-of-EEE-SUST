import React from 'react';
import { QuickStats } from '../../components/QuickStats';
import { TodayRoutine } from '../../components/TodayRoutine';
import { AttendanceGauge } from '../../components/AttendanceGauge';
import { DashboardHero } from './DashboardHero';
import { useDashboardSummary } from '../../hooks/useDashboardSummary';

export const CrDashboardPage = () => {
  const { data, isLoading } = useDashboardSummary();
  const s = data?.student;

  return (
    <div className="space-y-6 relative z-10">
      <DashboardHero
        consoleName="02 // CR CONSOLE"
        roleName="CLASS REPRESENTATIVE"
        unreadNotifications={s?.unread_notifications}
      />
      <QuickStats data={s} loading={isLoading} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TodayRoutine routine={s?.routine} loading={isLoading} />
        <AttendanceGauge data={s} loading={isLoading} />
      </div>
    </div>
  );
};
