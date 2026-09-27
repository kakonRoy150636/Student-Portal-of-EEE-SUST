import React from 'react';
import { DashboardHero } from './DashboardHero';
import { TeacherQuickStats } from './TeacherQuickStats';
import { TodayRoutine } from '../../components/TodayRoutine';
import { useDashboardSummary } from '../../hooks/useDashboardSummary';

export const TeacherDashboardPage = () => {
  const { data, isLoading } = useDashboardSummary();
  const t = data?.teacher;

  return (
    <div className="space-y-6">
      <DashboardHero
        roleName="TEACHER"
        unreadNotifications={t?.unread_notifications}
        greetingHint="Assigned courses, today’s classes, and pending reviews."
      />
      <TeacherQuickStats data={t} loading={isLoading} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TodayRoutine routine={[]} loading={false} />
        <section className="surface p-5">
          <h2 className="font-display text-base font-semibold text-[var(--text)]">Pending actions</h2>
          <ul className="mt-4 space-y-2 text-sm">
            <li className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-2">
              <span className="text-[var(--text-muted)]">Lab borrow requests</span>
              <span className="font-semibold text-[var(--text)]">{t?.pending_equipment_requests ?? 0} pending</span>
            </li>
            <li className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-2">
              <span className="text-[var(--text-muted)]">Room reservations</span>
              <span className="font-semibold text-[var(--text)]">{t?.pending_room_requests ?? 0} pending</span>
            </li>
            <li className="flex items-center justify-between gap-3">
              <span className="text-[var(--text-muted)]">Project proposals</span>
              <span className="font-semibold text-[var(--text)]">{t?.pending_project_proposals ?? 0} pending</span>
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
};
