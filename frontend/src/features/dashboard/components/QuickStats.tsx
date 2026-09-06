import React from 'react';
import { StatCard } from '@/components/shared/StatCard';
import { Clock, BookOpen, AlertCircle } from 'lucide-react';

export const QuickStats = () => (
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
    <StatCard title="Attendance Score" value="88.5%" icon={<Clock className="h-5 w-5 text-emerald-600" />} />
    <StatCard title="Current Credits" value="19.5 cr" icon={<BookOpen className="h-5 w-5 text-blue-600" />} />
    <StatCard title="Lab Reports Due" value="1 Pending" icon={<AlertCircle className="h-5 w-5 text-purple-600" />} />
  </div>
);
