import React from 'react';
import { DashboardHero } from './DashboardHero';
import { TeacherQuickStats } from './TeacherQuickStats';
import { TodayRoutine } from '../../components/TodayRoutine';
import { useDashboardSummary } from '../../hooks/useDashboardSummary';

export const TeacherDashboardPage = () => {
  const { data, isLoading } = useDashboardSummary();
  const t = data?.teacher;

  return (
    <div className="space-y-6 relative z-10">
      <DashboardHero
        consoleName="03 // FACULTY CONSOLE"
        roleName="TEACHER"
        unreadNotifications={t?.unread_notifications}
      />
      <TeacherQuickStats data={t} loading={isLoading} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TodayRoutine routine={[]} loading={false} />
        <section className="hud-box corner-brackets rounded-xl p-5">
          <h2 className="font-mono text-sm font-bold text-slate-300 mb-3">Your queues</h2>
          <ul className="text-xs font-mono text-slate-400 space-y-2">
            <li className="flex items-center justify-between gap-3 border-b border-slate-800/60 pb-2">
              <span>Lab borrow requests</span>
              <span className="font-bold text-slate-200">{t?.pending_equipment_requests ?? 0} pending</span>
            </li>
            <li className="flex items-center justify-between gap-3 border-b border-slate-800/60 pb-2">
              <span>Room reservations</span>
              <span className="font-bold text-slate-200">{t?.pending_room_requests ?? 0} pending</span>
            </li>
            <li className="flex items-center justify-between gap-3">
              <span>Project proposals</span>
              <span className="font-bold text-slate-200">{t?.pending_project_proposals ?? 0} pending</span>
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
};
