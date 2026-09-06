import React from 'react';
import { ScheduleCalendar } from '../components/ScheduleCalendar';

export default function SchedulePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Class Routine</h1>
      <ScheduleCalendar />
    </div>
  );
}
