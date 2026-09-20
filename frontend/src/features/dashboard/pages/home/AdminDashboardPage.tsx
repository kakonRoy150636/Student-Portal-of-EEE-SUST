import React from 'react';
import { DashboardHero } from './DashboardHero';

export const AdminDashboardPage = () => (
  <div className="space-y-6 relative z-10"><DashboardHero consoleName="00 // ADMIN CONSOLE" roleName="SUPER ADMIN" /><section className="hud-box corner-brackets rounded-xl p-5"><h2 className="font-mono text-sm font-bold text-cyan-300 mb-3">Administration Overview</h2><ul className="text-xs font-mono text-slate-300 list-disc pl-5 space-y-1"><li>Approve teacher, CR and ER accounts</li><li>Manage users and roles</li><li>Oversee room bookings</li><li>View system telemetry</li></ul></section></div>
);