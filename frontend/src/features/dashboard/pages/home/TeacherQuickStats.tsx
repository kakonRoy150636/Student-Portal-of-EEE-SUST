import React from 'react';
import { StatCard } from '@/components/shared/StatCard';
import { BookOpen, Calendar, GraduationCap, AlertCircle, Bell } from 'lucide-react';
import type { TeacherSummary } from '@/features/dashboard/types/dashboard';

interface TeacherQuickStatsProps {
  data?: TeacherSummary | null;
  loading?: boolean;
}

/** Faculty tiles, all from live aggregates. */
export const TeacherQuickStats = ({ data, loading = false }: TeacherQuickStatsProps) => {
  const reviews = (data?.pending_equipment_requests ?? 0) + (data?.pending_room_requests ?? 0)
    + (data?.pending_project_proposals ?? 0);

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Assigned Courses"
        value={loading ? undefined : data?.assigned_courses ?? 0}
        icon={<BookOpen className="h-5 w-5" />}
        subtitle="Offerings you are assigned to teach"
        tag="MEASURED // LOAD"
        loading={loading}
      />
      <StatCard
        title="Students"
        value={loading ? undefined : data?.students_taught ?? 0}
        icon={<GraduationCap className="h-5 w-5" />}
        subtitle="Distinct students across those courses"
        tag="MEASURED // REACH"
        loading={loading}
      />
      <StatCard
        title="Today's Classes"
        value={loading ? undefined : data?.today_classes ?? 0}
        icon={<Calendar className="h-5 w-5" />}
        subtitle="Sessions on your timetable for today"
        tag="MEASURED // SCHEDULE"
        tone={data?.today_classes ? 'accent' : 'muted'}
        loading={loading}
        href="/schedule"
      />
      <StatCard
        title="Pending Reviews"
        value={loading ? undefined : reviews}
        icon={<AlertCircle className="h-5 w-5" />}
        subtitle="Lab, room and project requests awaiting you"
        tag="MEASURED // QUEUE"
        tone={reviews ? 'warn' : 'muted'}
        loading={loading}
      />
    </div>
  );
};
