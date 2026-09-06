import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

export const AttendanceGauge = () => (
  <Card>
    <CardHeader><CardTitle className="text-base">Eligibility Threshold</CardTitle></CardHeader>
    <CardContent>
      <p className="text-xs text-slate-500">Above collegiate requirement (75%). You are eligible for final semester examination.</p>
    </CardContent>
  </Card>
);
