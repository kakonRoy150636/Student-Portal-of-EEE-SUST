import React from 'react';
import { QuickStats } from '../../components/QuickStats';
import { TodayRoutine } from '../../components/TodayRoutine';
import { AttendanceGauge } from '../../components/AttendanceGauge';
import { DashboardHero } from './DashboardHero';

export const StudentDashboardPage = () => (
  <div className="space-y-6 relative z-10">
    <DashboardHero consoleName="01 // STUDENT CONSOLE" roleName="STUDENT" />
    <QuickStats />
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2"><TodayRoutine /><AttendanceGauge /></div>
  </div>
);