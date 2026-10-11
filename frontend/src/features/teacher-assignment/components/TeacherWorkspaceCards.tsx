import React from 'react';
import type { UseQueryResult } from '@tanstack/react-query';
import { ArrowUpRight, Bell, CalendarDays, GraduationCap, Users } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getErrorMessage } from '@/lib/errors';
import type { CourseOffering } from '@/types/academic';
import type { CourseWorkspace } from '@/types/courseWorkspace';

export function TeacherWorkspaceCards({ offerings, queries }: { offerings: CourseOffering[]; queries: UseQueryResult<CourseWorkspace>[] }) {
  if (offerings.length === 0) return null;
  return (
    <section aria-labelledby="teacher-workspaces-heading" className="space-y-3">
      <div><p className="kicker">Course workspaces</p><h2 id="teacher-workspaces-heading" className="mt-1 font-display text-lg font-semibold">Your eligible courses</h2><p className="mt-1 text-sm text-[var(--text-muted)]">Open an assigned or provided course to manage its announcements, resources, roster, and settings.</p></div>
      <div className="grid gap-4 lg:grid-cols-2">
        {offerings.map((offering, index) => <TeacherWorkspaceCard key={offering.id} offering={offering} query={queries[index]} />)}
      </div>
    </section>
  );
}

function TeacherWorkspaceCard({ offering, query }: { offering: CourseOffering; query?: UseQueryResult<CourseWorkspace> }) {
  const workspace = query?.data;
  const teachers = workspace?.authorized_teachers ?? offering.assigned_teachers;
  const lastActivity = workspace?.recent_activity[0];
  const lastActivityDate = lastActivity ? new Date(lastActivity.updated_at || lastActivity.created_at) : null;
  const displayLastActivity = lastActivityDate && !Number.isNaN(lastActivityDate.getTime()) ? lastActivityDate.toLocaleString() : 'No recorded activity';
  return (
    <Card className="overflow-hidden">
      <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><p className="font-mono text-sm font-semibold text-[var(--accent-bright)]">{workspace?.course.course_code ?? offering.course_code}</p><Badge variant={(workspace?.offering_status ?? offering.publication_status) === 'published' ? 'success' : 'secondary'}>{workspace?.offering_status ?? offering.publication_status}</Badge></div><CardTitle className="mt-2 break-words">{workspace?.course.title ?? offering.course_title}</CardTitle></div>
        <a className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-[var(--accent-bright)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" href={`/teacher/courses/${offering.id}`}>Open workspace<ArrowUpRight className="h-4 w-4" aria-hidden="true" /></a>
      </CardHeader>
      <CardContent>
        {query?.isPending && <p role="status" className="mb-4 text-sm text-[var(--text-muted)]">Loading workspace summary…</p>}
        {query?.isError && <div className="mb-4 flex flex-col gap-2 rounded-lg border border-[var(--danger)] bg-[var(--danger-soft)] p-3 text-sm" role="alert"><p className="text-[var(--danger)]">Workspace summary unavailable: {getErrorMessage(query.error, 'Please retry.')}</p><Button size="sm" variant="outline" className="self-start" onClick={() => void query.refetch()} disabled={query.isFetching}>Retry summary</Button></div>}
        <div className="grid gap-3 sm:grid-cols-2">
          <Meta icon={<GraduationCap className="h-4 w-4" />} label="Credit" value={String(workspace?.course.credit_hours ?? offering.credit_hours)} />
          <Meta icon={<CalendarDays className="h-4 w-4" />} label="Semester / target" value={`${workspace?.semester.title ?? offering.semester_title} · ${workspace?.semester.target_term ?? offering.target_term ?? 'Not set'}`} />
          <Meta icon={<Users className="h-4 w-4" />} label="Enrollment" value={workspace ? String(workspace.active_enrollment_count) : 'Unavailable'} />
          <Meta icon={<Bell className="h-4 w-4" />} label="Unread announcements" value={workspace ? String(workspace.unread_announcement_count) : 'Unavailable'} />
        </div>
        <div className="mt-4 border-t border-[var(--border)] pt-3"><p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-subtle)]">Authorized teachers</p>{teachers.length > 0 ? <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-[var(--text-muted)]">{teachers.map((teacher) => <li key={`${offering.id}-${teacher.teacher_id}`}>{teacher.teacher_name}</li>)}</ul> : <p className="mt-2 text-sm text-[var(--text-muted)]">No teacher listed</p>}<p className="mt-3 text-xs text-[var(--text-subtle)]">Last activity: {displayLastActivity}</p></div>
      </CardContent>
    </Card>
  );
}

function Meta({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="flex min-w-0 gap-2 rounded-lg bg-[var(--surface-muted)] p-3"><span className="mt-0.5 shrink-0 text-[var(--accent-bright)]">{icon}</span><div className="min-w-0"><p className="text-xs text-[var(--text-subtle)]">{label}</p><p className="mt-1 truncate text-sm font-medium" title={value}>{value}</p></div></div>;
}
