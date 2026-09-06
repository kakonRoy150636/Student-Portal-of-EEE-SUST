import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export const ScheduleCalendar = () => {
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday'];
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
      {days.map((day) => (
        <div key={day} className="space-y-2">
          <div className="p-2 bg-slate-100 dark:bg-slate-800 text-center font-bold text-xs rounded">{day}</div>
          <Card className="border-l-4 border-l-emerald-500">
            <CardHeader className="p-3 pb-1">
              <span className="font-bold text-xs">EEE 311</span>
              <CardTitle className="text-[11px] text-slate-400">09:00 - 10:30 AM</CardTitle>
            </CardHeader>
            <CardContent className="p-3 pt-0 text-[11px] text-slate-500">Room 304</CardContent>
          </Card>
        </div>
      ))}
    </div>
  );
};
