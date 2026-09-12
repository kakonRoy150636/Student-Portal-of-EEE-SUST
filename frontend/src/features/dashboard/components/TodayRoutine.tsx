import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Clock, MapPin, User, ArrowRight } from 'lucide-react';

export const TodayRoutine = () => {
  const lectures = [
    {
      id: 1,
      code: 'EEE 311',
      title: 'Electrical Machines II',
      time: '09:00 AM - 10:30 AM',
      room: 'Room 304, IICT Building',
      instructor: 'Dr. M. Rahman',
      status: 'live' // 'live' | 'upcoming' | 'completed'
    },
    {
      id: 2,
      code: 'EEE 313',
      title: 'Microprocessor & Interfacing',
      time: '11:00 AM - 12:30 PM',
      room: 'Micro Lab 2, EEE Dept',
      instructor: 'Engr. K. Ahmed',
      status: 'upcoming'
    }
  ];

  return (
    <Card className="border border-slate-200/80 bg-white/70 backdrop-blur-xl dark:border-slate-800/80 dark:bg-slate-900/60">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base font-semibold">Today's Class Schedule</CardTitle>
        <span className="text-xs text-slate-400">3 Classes Today</span>
      </CardHeader>
      <CardContent className="space-y-3">
        {lectures.map((lecture) => {
          const isLive = lecture.status === 'live';
          return (
            <div
              key={lecture.id}
              className={`group relative rounded-xl border p-4 transition-all duration-200 ${
                isLive
                  ? 'border-emerald-500/50 bg-emerald-500/[0.03] shadow-sm ring-1 ring-emerald-500/20 dark:border-emerald-500/30 dark:bg-emerald-950/20'
                  : 'border-slate-100 bg-slate-50/70 hover:border-slate-200 dark:border-slate-800/60 dark:bg-slate-800/40 dark:hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-xs tracking-wide text-emerald-600 dark:text-emerald-400">
                      {lecture.code}
                    </span>
                    {isLive && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">
                        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                        Live Now
                      </span>
                    )}
                  </div>
                  <h4 className="mt-1 font-semibold text-sm text-slate-900 dark:text-slate-100">
                    {lecture.title}
                  </h4>
                </div>

                <div className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                  <Clock className="h-3.5 w-3.5" />
                  <span>{lecture.time}</span>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                <div className="flex items-center gap-1">
                  <MapPin className="h-3.5 w-3.5 text-slate-400" />
                  <span>{lecture.room}</span>
                </div>
                <div className="flex items-center gap-1">
                  <User className="h-3.5 w-3.5 text-slate-400" />
                  <span>{lecture.instructor}</span>
                </div>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
};
