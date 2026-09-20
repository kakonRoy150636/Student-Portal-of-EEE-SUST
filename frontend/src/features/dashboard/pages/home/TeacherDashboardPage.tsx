import React from 'react';
import { DashboardHero } from './DashboardHero';
import { TeacherQuickStats } from './TeacherQuickStats';

export const TeacherDashboardPage = () => (
  <div className="space-y-6 relative z-10">
    <DashboardHero consoleName="03 // FACULTY CONSOLE" roleName="TEACHER" />
    <TeacherQuickStats />
    <section className="hud-box corner-brackets rounded-xl p-5">
      <h2 className="font-mono text-sm font-bold text-cyan-300 mb-3">Faculty Tasks</h2>
      <ul className="text-xs font-mono text-slate-300 list-disc pl-5 space-y-1">
        <li>Record student attendance for assigned courses</li>
        <li>Review room booking requests</li>
        <li>Manage lab sessions and equipment access</li>
        <li>Review student assignments and projects</li>
      </ul>
    </section>
  </div>
);