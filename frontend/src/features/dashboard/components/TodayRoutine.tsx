import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

export const TodayRoutine = () => (
  <Card>
    <CardHeader><CardTitle className="text-base">Today's Lectures</CardTitle></CardHeader>
    <CardContent className="space-y-3">
      <div className="p-3 border-l-4 border-l-emerald-500 bg-slate-50 dark:bg-slate-800 rounded">
        <p className="font-bold text-sm">EEE 311: Electrical Machines II</p>
        <p className="text-xs text-slate-400">09:00 AM - 10:30 AM | Room 304, IICT</p>
      </div>
    </CardContent>
  </Card>
);
