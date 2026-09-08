import React from 'react';
import { StatCard } from '@/components/shared/StatCard';
import { CheckCircle2, BookOpen, AlertCircle, Award } from 'lucide-react';

export const QuickStats = () => (
  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
    <StatCard
      title="Attendance Telemetry"
      value="88.5%"
      icon={<CheckCircle2 className="h-5 w-5" />}
      trend={{ value: "+2.1% OK", isPositive: true }}
      subtitle="Collegiate standing"
      tag="SENSOR // ATTN"
      accentColor="cyan"
    />
    <StatCard
      title="Credit Registry"
      value="19.5 CR"
      icon={<BookOpen className="h-5 w-5" />}
      subtitle="6 Theory • 3 Labs"
      tag="LOAD // TERM 3-1"
      accentColor="cyan"
    />
    <StatCard
      title="Pending Reports"
      value="01 PENDING"
      icon={<AlertCircle className="h-5 w-5" />}
      trend={{ value: "T-48h DUE", isPositive: false }}
      subtitle="EEE 312: Machines"
      tag="SUBMIT // URGENT"
      accentColor="crimson"
    />
    <StatCard
      title="Cumulative Index"
      value="3.84 CGPA"
      icon={<Award className="h-5 w-5" />}
      trend={{ value: "+0.06 DELTA", isPositive: true }}
      subtitle="Batch Rank: Top 5%"
      tag="METRIC // ACAD"
      accentColor="cyan"
    />
  </div>
);