import React from 'react';
import { QuickStats } from '../components/QuickStats';
import { TodayRoutine } from '../components/TodayRoutine';
import { AttendanceGauge } from '../components/AttendanceGauge';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Academic Overview</h1>
        <p className="text-xs text-slate-500">Term 3-1 | Department of Electrical & Electronic Engineering</p>
      </div>
      <QuickStats />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TodayRoutine />
        <AttendanceGauge />
      </div>
    </div>
  );
}
