import React, { ReactNode } from 'react';
import { Card, CardContent } from '@/components/ui/card';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
}

export const StatCard = ({ title, value, icon }: StatCardProps) => (
  <Card>
    <CardContent className="flex items-center justify-between p-6">
      <div>
        <p className="text-xs font-medium text-slate-500">{title}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
      <div className="rounded-lg bg-slate-100 p-3 text-slate-700 dark:bg-slate-800 dark:text-slate-200">
        {icon}
      </div>
    </CardContent>
  </Card>
);
