import React from 'react';
import { DashboardHero } from './DashboardHero';

export const ErDashboardPage = () => (
  <div className="space-y-6 relative z-10"><DashboardHero consoleName="04 // ER CONSOLE" roleName="ER / LAB ASSISTANT" /><section className="hud-box corner-brackets rounded-xl p-5"><h2 className="font-mono text-sm font-bold text-cyan-300 mb-3">Lab Operations</h2><ul className="text-xs font-mono text-slate-300 list-disc pl-5 space-y-1"><li>Manage lab equipment inventory</li><li>Approve lab access requests</li><li>Monitor equipment usage</li><li>Report maintenance issues</li></ul></section></div>
);