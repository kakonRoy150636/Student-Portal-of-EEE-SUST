import React from 'react';
import { RollCallGrid } from '../components/RollCallGrid';

export default function AttendancePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Attendance Records</h1>
      <RollCallGrid />
    </div>
  );
}
