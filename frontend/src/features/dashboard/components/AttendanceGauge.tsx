import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { CheckCircle2, AlertTriangle } from 'lucide-react';

export const AttendanceGauge = () => {
  const percentage = 88.5;
  const threshold = 75.0;
  const isEligible = percentage >= threshold;

  // SVG circular gauge calculations
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <Card className="border border-slate-200/80 bg-white/70 backdrop-blur-xl dark:border-slate-800/80 dark:bg-slate-900/60">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">Eligibility Threshold</CardTitle>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${
              isEligible
                ? 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-400 dark:ring-emerald-500/20'
                : 'bg-amber-50 text-amber-700 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-400 dark:ring-amber-500/20'
            }`}
          >
            {isEligible ? <CheckCircle2 className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
            {isEligible ? 'Collegiate' : 'Non-Collegiate'}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center justify-center gap-6 py-2 sm:flex-row">
          {/* Circular SVG Gauge */}
          <div className="relative flex items-center justify-center">
            <svg className="h-36 w-36 -rotate-90 transform">
              <circle
                cx="72"
                cy="72"
                r={radius}
                className="stroke-slate-100 dark:stroke-slate-800"
                strokeWidth="10"
                fill="transparent"
              />
              <circle
                cx="72"
                cy="72"
                r={radius}
                className="stroke-emerald-500 transition-all duration-1000 ease-out"
                strokeWidth="10"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                fill="transparent"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="text-2xl font-black text-slate-900 dark:text-slate-100">{percentage}%</span>
              <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">Total Avg</span>
            </div>
          </div>

          {/* Details breakdown */}
          <div className="flex-1 space-y-3 text-xs">
            <div className="flex justify-between rounded-lg bg-slate-50 p-2.5 dark:bg-slate-800/50">
              <span className="text-slate-500">Minimum Exam Cutoff</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">{threshold}%</span>
            </div>
            <div className="flex justify-between rounded-lg bg-slate-50 p-2.5 dark:bg-slate-800/50">
              <span className="text-slate-500">Safety Buffer</span>
              <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                +{(percentage - threshold).toFixed(1)}% above cutoff
              </span>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-400">
              You meet the departmental collegiate requirements and are cleared for final examinations.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
