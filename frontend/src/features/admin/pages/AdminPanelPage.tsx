import React from 'react';
import { Card, CardContent } from '@/components/ui/card';

export default function AdminPanelPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">System Administration</h1>
      <Card>
        <CardContent className="p-5">
          <p className="font-bold text-sm">SUST EEE Administration Console</p>
          <p className="text-xs text-slate-400 mt-1">Manage student batches, approve room allocations, configure semester offerings.</p>
        </CardContent>
      </Card>
    </div>
  );
}
