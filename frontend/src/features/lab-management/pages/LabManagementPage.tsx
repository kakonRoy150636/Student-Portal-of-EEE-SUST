import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function LabManagementPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Smart Lab Management</h1>
      <Card>
        <CardContent className="p-5">
          <div className="flex justify-between items-center">
            <div>
              <p className="font-bold text-sm">Rigol DS1054Z Digital Oscilloscope</p>
              <p className="text-xs text-slate-400">Tag: SUST-EEE-EL-042 | Electronics Lab Bench 4</p>
            </div>
            <Badge variant="default">Operational</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
