import React from 'react';
import { StatCard } from '@/components/shared/StatCard';
import { CheckCircle2, BookOpen, AlertCircle, Award } from 'lucide-react';

export const QuickStats = () => (
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <StatCard
      title="Attendance Score"
      value="88.5%"
      icon={<CheckCircle2 className="h-5 w-5 text-emerald-500" />}
      trend={{ value: "+2.1%", isPositive: true }}
      subtitle="Collegiate standing"
    />
    <StatCard
      title="Enrolled Credits"
      value="19.5 cr"
      icon={<BookOpen className="h-5 w-5 text-blue-500" />}
      subtitle="6 theory, 3 labs"
    />
    <StatCard
      title="Lab Reports"
      value="1 Pending"
      icon={<AlertCircle className="h-5 w-5 text-amber-500" />}
      trend={{ value: "Due in 2 days", isPositive: false }}
      subtitle="EEE 312: Machines Lab"
    />
    <StatCard
      title="Current CGPA"
      value="3.84"
      icon={<Award className="h-5 w-5 text-purple-500" />}
      trend={{ value: "+0.06", isPositive: true }}
      subtitle="Top 5% in batch"
    />
  </div>
);
