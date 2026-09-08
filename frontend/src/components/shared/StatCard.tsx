import React, { ReactNode } from 'react';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  trend?: {
    value: string;
    isPositive: boolean;
  };
  subtitle?: string;
  tag?: string;
  accentColor?: 'crimson' | 'cyan';
}

export const StatCard = ({
  title,
  value,
  icon,
  trend,
  subtitle,
  tag = 'SYS.PARAM',
  accentColor = 'cyan'
}: StatCardProps) => {
  const isCrimson = accentColor === 'crimson';

  return (
    <div className="hud-box corner-brackets relative rounded-xl p-5 overflow-hidden">
      <div className="flex items-center justify-between pb-3 text-[10px] font-mono tracking-widest text-slate-500 border-b border-slate-800/80">
        <span className="flex items-center gap-1.5">
          <span className={`h-1.5 w-1.5 rounded-full ${isCrimson ? 'bg-[#FF1E56]' : 'bg-[#00F0FF]'} animate-ping`} />
          {tag}
        </span>
        <span className="text-slate-600">ID:0x7B2</span>
      </div>

      <div className="mt-4 flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            {title}
          </p>
          <p className="text-2xl font-black tracking-tight text-white font-mono">
            {value}
          </p>
        </div>
        <div className={`flex h-11 w-11 items-center justify-center rounded-lg border ${
          isCrimson 
            ? 'border-[#FF1E56]/40 bg-[#FF1E56]/10 text-[#FF1E56]' 
            : 'border-[#00F0FF]/40 bg-[#00F0FF]/10 text-[#00F0FF]'
        }`}>
          {icon}
        </div>
      </div>

      {(trend || subtitle) && (
        <div className="mt-4 flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs font-mono">
          {trend && (
            <span
              className={`inline-flex items-center gap-0.5 font-bold ${
                trend.isPositive ? 'text-[#00F0FF]' : 'text-[#FF1E56]'
              }`}
            >
              {trend.isPositive ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
              {trend.value}
            </span>
          )}
          {subtitle && (
            <span className="text-slate-500 text-[11px] truncate">
              {subtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );
};