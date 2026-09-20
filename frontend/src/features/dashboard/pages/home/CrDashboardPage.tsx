import React from 'react';
import { QuickStats } from '../../components/QuickStats';
import { TodayRoutine } from '../../components/TodayRoutine';
import { AttendanceGauge } from '../../components/AttendanceGauge';
import { DashboardHero } from './DashboardHero';

export const CrDashboardPage = () => (
  <div className="space-y-6 relative z-10">
    <DashboardHero consoleName="02 // CR CONSOLE" roleName="CLASS REPRESENTATIVE" />
    <QuickStats />
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2"><TodayRoutine /><AttendanceGauge /></div>
    <section className="hud-box corner-brackets rounded-xl p-5"><h2 className="font-mono text-sm font-bold text-cyan-300 mb-3">Class Representative Tasks</h2><ul className="text-xs font-mono text-slate-300 list-disc pl-5 space-y-1"><li>Coordinate class schedule changes</li><li>Book rooms for batch events</li><li>Relay attendance issues to teachers</li><li>Share resources with the batch</li></ul></section>
  </div>
);