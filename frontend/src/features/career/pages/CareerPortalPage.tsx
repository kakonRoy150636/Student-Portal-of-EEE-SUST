import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function CareerPortalPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Career & Higher Study Portal</h1>
      <Card>
        <CardContent className="p-5 flex justify-between items-center">
          <div>
            <p className="font-bold text-sm">VLSI Design Engineering Intern</p>
            <p className="text-xs text-slate-400">Neural Semiconductor • Dhaka • Deadline: Oct 15, 2026</p>
          </div>
          <Badge>Internship</Badge>
        </CardContent>
      </Card>
    </div>
  );
}
