import React from 'react';
import { QuickStats } from '../components/QuickStats';
import { TodayRoutine } from '../components/TodayRoutine';
import { AttendanceGauge } from '../components/AttendanceGauge';
import { Radio, Cpu, Bell } from 'lucide-react';

export default function DashboardPage() {
  return (
    <div className="space-y-6 relative z-10">
      {/* Sci-Fi HUD Hero Banner */}
      <div className="hud-box corner-brackets rounded-2xl p-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-full bg-gradient-to-l from-[#FF1E56]/10 via-[#00F0FF]/5 to-transparent pointer-events-none" />

        <div className="relative z-10 flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div className="space-y-2">
            <div className="flex items-center gap-3 font-mono text-xs">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-[#FF1E56]/10 border border-[#FF1E56]/30 text-[#FF1E56] font-bold text-[10px] tracking-wider uppercase">
                <Radio className="h-3 w-3 animate-pulse" />
                01 // COMMAND CONSOLE
              </span>
              <span className="text-slate-400 text-[11px]">
                TERM 3-1 • FALL 2026
              </span>
            </div>

            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white font-mono uppercase">
              KAKON CHANDRO ROY
            </h1>
            <p className="text-xs font-mono text-cyan-400">
              DEPARTMENT OF ELECTRICAL & ELECTRONIC ENGINEERING // SUST
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-4 font-mono text-xs space-y-2">
            <div className="flex items-center justify-between gap-4">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Cpu className="h-3.5 w-3.5 text-cyan-400" />
                SYSTEM STATUS:
              </span>
              <span className="text-[#00F0FF] font-bold">OPTIMAL</span>
            </div>
            <div className="flex items-center justify-between gap-4 border-t border-slate-800/80 pt-2">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Bell className="h-3.5 w-3.5 text-[#FF1E56]" />
                UPCOMING EXAM:
              </span>
              <span className="text-[#FF1E56] font-bold">MACHINES II (T-12d)</span>
            </div>
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
