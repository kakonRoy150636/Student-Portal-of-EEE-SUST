import React, { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card';
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
}

export const StatCard = ({ title, value, icon, trend, subtitle }: StatCardProps) => (
  <Card className="relative overflow-hidden border border-slate-200/80 bg-white/70 backdrop-blur-xl transition-all duration-300 hover:-translate-y-1 hover:border-emerald-500/40 hover:shadow-lg hover:shadow-emerald-500/5 dark:border-slate-800/80 dark:bg-slate-900/60">
    {/* সূক্ষ্ম ব্যাকগ্রাউন্ড অ্যাকসেন্ট */}
    <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-emerald-500/5 blur-2xl dark:bg-emerald-500/10" />

    <CardContent className="p-5">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-xs font-medium tracking-wider text-slate-500 dark:text-slate-400 uppercase">
            {title}
          </p>
          <p className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-slate-50">
            {value}
          </p>
        </div>
        <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100/80 ring-1 ring-slate-200 text-slate-700 transition-colors dark:bg-slate-800/80 dark:ring-slate-700/60 dark:text-slate-200">
          {icon}
        </div>
      </div>

      {(trend || subtitle) && (
        <div className="mt-4 flex items-center gap-2 pt-3 border-t border-slate-100 dark:border-slate-800/60 text-xs">
          {trend && (
            <span
              className={`inline-flex items-center gap-0.5 font-semibold ${
                trend.isPositive ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
              }`}
            >
              {trend.isPositive ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
              {trend.value}
            </span>
          )}
          {subtitle && (
            <span className="text-slate-400 dark:text-slate-500 truncate">
              {subtitle}
            </span>
          )}
        </div>
      )}
    </CardContent>
  </Card>
);
