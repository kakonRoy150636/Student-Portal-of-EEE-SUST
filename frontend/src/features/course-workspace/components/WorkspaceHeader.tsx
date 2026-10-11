import React from 'react';
import { ArrowLeft, Bell, CalendarDays, GraduationCap, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import type { CourseWorkspace } from '@/types/courseWorkspace';

function workspaceBackPath(manager: boolean): string {
  return manager ? '/teacher-assignment' : '/course-selection';
}

export function WorkspaceHeader({ workspace, manager }: { workspace: CourseWorkspace; manager: boolean }) {
  const { course, semester } = workspace;
  return (
    <Card className="overflow-hidden border-[var(--accent-edge)] bg-[var(--accent-soft)]/20">
      <CardContent className="p-5 sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <Link
              to={workspaceBackPath(manager)}
              className="mb-3 inline-flex items-center gap-1.5 text-sm font-semibold text-[var(--text-muted)] hover:text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back to {manager ? 'course assignment' : 'course selection'}
            </Link>
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-mono text-sm font-semibold tracking-wide text-[var(--accent-bright)]">{course.course_code}</p>
              <Badge variant={workspace.offering_status === 'published' ? 'success' : 'secondary'}>
                {workspace.offering_status}
              </Badge>
              {!semester.is_active && <Badge variant="secondary">Inactive semester</Badge>}
            </div>
            <h1 className="mt-2 break-words font-display text-2xl font-bold tracking-tight text-[var(--text)]">{course.title}</h1>
            <p className="mt-2 max-w-3xl text-sm text-[var(--text-muted)]">
              {course.description || 'Course workspace for announcements, resources, schedules, and enrolled learners.'}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[28rem]">
            <SummaryStat icon={<CalendarDays className="h-4 w-4" />} label="Term" value={semester.target_term ?? 'Not set'} />
            <SummaryStat icon={<GraduationCap className="h-4 w-4" />} label="Credits" value={String(course.credit_hours)} />
            <SummaryStat icon={<Users className="h-4 w-4" />} label="Enrolled" value={String(workspace.active_enrollment_count)} />
            <SummaryStat icon={<Bell className="h-4 w-4" />} label="Unread" value={String(workspace.unread_announcement_count)} />
          </div>
        </div>
        <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 border-t border-[var(--border)] pt-4 text-xs text-[var(--text-muted)]">
          <span>{semester.title}</span>
          <span>{course.type.replace(/_/g, ' ')}</span>
          <span>{workspace.authorized_teachers.length} authorized teacher{workspace.authorized_teachers.length === 1 ? '' : 's'}</span>
          <span>{semester.start_date} – {semester.end_date}</span>
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryStat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)]/70 p-3">
      <div className="flex items-center gap-1.5 text-[var(--text-muted)]">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className="mt-1 truncate font-mono text-lg font-semibold tabular-nums text-[var(--text)]">{value}</p>
    </div>
  );
}
