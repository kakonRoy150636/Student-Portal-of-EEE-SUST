import React from 'react';
import { QuickStats } from '../components/QuickStats';
import { TodayRoutine } from '../components/TodayRoutine';
import { AttendanceGauge } from '../components/AttendanceGauge';
import { Sparkles, Calendar } from 'lucide-react';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Sleek Hero Header */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200/80 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 text-white shadow-xl">
        <div className="absolute right-0 top-0 h-full w-1/3 bg-gradient-to-l from-emerald-500/10 to-transparent pointer-events-none" />
        <div className="relative z-10 flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400 ring-1 ring-emerald-500/20">
              <Sparkles className="h-3.5 w-3.5" />
              Fall Semester 2026
            </div>
            <h1 className="mt-2 text-2xl font-bold tracking-tight md:text-3xl">
              Welcome back, Kakon 👋
            </h1>
            <p className="mt-1 text-xs text-slate-300">
              Department of Electrical & Electronic Engineering • Term 3-1
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2.5 backdrop-blur-md text-xs font-medium">
            <Calendar className="h-4 w-4 text-emerald-400" />
            <span>Next Exam: Machine II Midterm in 12 days</span>
          </div>
        </div>
      </div>

      <QuickStats />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <TodayRoutine />
        <AttendanceGauge />
      </div>
    </div>
  );
}
