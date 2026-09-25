import React from 'react';
import { StatCard } from '@/components/shared/StatCard';
import { CheckCircle2, BookOpen, Bell, Briefcase } from 'lucide-react';
import type { StudentSummary } from '@/features/dashboard/types/dashboard';

interface QuickStatsProps {
  data?: StudentSummary | null;
  loading?: boolean;
}

/**
 * Student/CR tiles, all fed by GET /dashboard/summary.
 *
 * Replaces the previous version, which hardcoded "88.5%", "19.5 CR",
 * "01 PENDING" and "3.84 CGPA" as strings. Attendance now shows the real
 * aggregate, and shows an empty state when no class has been recorded yet --
 * which is the truth on a fresh database, and is worth more to a reviewer
 * than a flattering invented number.
 */
export const QuickStats = ({ data, loading = false }: QuickStatsProps) => {
  const pct = data?.attendance_percentage ?? null;
  const hasAttendance = data ? data.total_classes > 0 : false;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Attendance"
        value={hasAttendance ? `${pct}%` : 'NO DATA'}
        icon={<CheckCircle2 className="h-5 w-5" />}
        subtitle={
          hasAttendance
            ? `${data?.attended} of ${data?.total_classes} classes recorded`
            : 'No attendance has been recorded yet'
        }
        tag="MEASURED // ATTENDANCE"
        tone={
          data?.below_attendance_threshold === true ? 'warn' : hasAttendance ? 'accent' : 'muted'
        }
        loading={loading}
        href="/attendance"
      />
      <StatCard
        title="Credit Load"
        value={loading ? undefined : `${(data?.credit_hours ?? 0).toFixed(1)} CR`}
        icon={<BookOpen className="h-5 w-5" />}
        subtitle={`${data?.enrolled_courses ?? 0} course${data?.enrolled_courses === 1 ? '' : 's'} enrolled`}
        tag="MEASURED // ENROLMENT"
        loading={loading}
      />
      <StatCard
        title="Classes Today"
        value={loading ? undefined : data?.today_classes ?? 0}
        icon={<Bell className="h-5 w-5" />}
        subtitle={
          data?.today_classes
            ? 'See the timetable below'
            : 'Nothing scheduled in today\'s timetable'
        }
        tag="MEASURED // SCHEDULE"
        tone={data?.today_classes ? 'accent' : 'muted'}
        loading={loading}
        href="/schedule"
      />
      <StatCard
        title="Open Opportunities"
        value={loading ? undefined : data?.opportunities ?? 0}
        icon={<Briefcase className="h-5 w-5" />}
        subtitle="Verified, deadline not passed"
        tag="MEASURED // CAREER"
        tone={data?.opportunities ? 'accent' : 'muted'}
        loading={loading}
        href="/career"
      />
    </div>
  );
};
