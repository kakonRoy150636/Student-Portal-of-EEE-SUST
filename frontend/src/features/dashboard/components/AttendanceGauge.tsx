import React from 'react';
import { ShieldCheck, Crosshair } from 'lucide-react';

export const AttendanceGauge = () => {
  const percentage = 88.5;
  const threshold = 75.0;
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <div className="hud-box corner-brackets rounded-xl p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 font-mono text-xs">
        <span className="text-slate-300 flex items-center gap-1.5 font-bold uppercase tracking-wider">
          <Crosshair className="h-4 w-4 text-[#FF1E56]" />
          TELEMETRY // COLLEGIATE SCAN
        </span>
        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded bg-[#00F0FF]/10 text-[#00F0FF] border border-[#00F0FF]/30">
          <ShieldCheck className="h-3 w-3" />
          CLEARANCE: GRANTED
        </span>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-6 py-4">
        {/* রেডার সার্কুলার গেজ */}
        <div className="relative flex items-center justify-center">
          <svg className="h-36 w-36 -rotate-90 transform">
            <circle
              cx="72"
              cy="72"
              r={radius}
              className="stroke-slate-800"
              strokeWidth="8"
              strokeDasharray="4 4"
              fill="transparent"
            />
            <circle
              cx="72"
              cy="72"
              r={radius}
              className="stroke-[#00F0FF] transition-all duration-1000 ease-out"
              strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              fill="transparent"
            />
          </svg>

          <div className="absolute flex flex-col items-center font-mono">
            <span className="text-2xl font-black text-white">{percentage}%</span>
            <span className="text-[9px] uppercase tracking-widest text-slate-400">SCORE</span>
          </div>
        </div>

        <div className="flex-1 space-y-2.5 font-mono text-xs w-full">
          <div className="flex justify-between rounded bg-slate-900/80 border border-slate-800 p-2">
            <span className="text-slate-400">THRESHOLD REQUIRED:</span>
            <span className="font-bold text-slate-200">{threshold}% MIN</span>
          </div>
          <div className="flex justify-between rounded bg-slate-900/80 border border-slate-800 p-2">
            <span className="text-slate-400">SAFETY TOLERANCE:</span>
            <span className="font-bold text-[#00F0FF]">
              +{(percentage - threshold).toFixed(1)}% MARGIN
            </span>
          </div>
          <div className="flex justify-between rounded bg-slate-900/80 border border-slate-800 p-2">
            <span className="text-slate-400">EXAM ELIGIBILITY:</span>
            <span className="font-bold text-[#FF1E56]">PERMITTED</span>
          </div>
        </div>
      </div>

      <div className="pt-3 border-t border-slate-800/80 text-[10px] font-mono text-slate-500">
        VERIFIED VIA EEE RFID ROLL-CALL SYSTEM // SYNCED
      </div>
    </div>
  );
};