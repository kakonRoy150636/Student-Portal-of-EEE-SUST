import React from 'react';
import { Card, CardContent } from '@/components/ui/card';

export default function ProjectHubPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Project Hub & Capstone Showcase</h1>
      <Card>
        <CardContent className="p-5">
          <p className="font-bold text-sm">Biomimetic Underwater Autonomous Vehicle</p>
          <p className="text-xs text-slate-400 mt-1">Supervisor: Dr. Md. Tasfiq Rahman | Team: Kakon, Tanij, Mehedi</p>
        </CardContent>
      </Card>
    </div>
  );
}
