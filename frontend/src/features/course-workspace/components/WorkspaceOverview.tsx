import React from 'react';
import { ArrowUpRight, BellPlus, BookOpen, CalendarDays, CheckSquare, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/shared/EmptyState';
import type { CourseAnnouncement, CourseWorkspace } from '@/types/courseWorkspace';
import { AnnouncementBody } from './AnnouncementBody';

interface WorkspaceOverviewProps {
  workspace: CourseWorkspace;
  manager: boolean;
  canManage?: boolean;
  onCreateAnnouncement: () => void;
  onOpenTab: (tab: 'announcements' | 'resources' | 'students' | 'assignments' | 'events' | 'questions' | 'settings') => void;
}

function activityDate(item: CourseAnnouncement): string {
  const value = item.updated_at || item.created_at;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleString();
}

export function WorkspaceOverview({ workspace, manager, canManage = true, onCreateAnnouncement, onOpenTab }: WorkspaceOverviewProps) {
  return (
    <div id="workspace-panel-overview" role="tabpanel" aria-labelledby="workspace-tab-overview" className="space-y-5">
      <section aria-labelledby="workspace-summary-heading">
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="kicker">Course overview</p>
            <h2 id="workspace-summary-heading" className="mt-1 font-display text-lg font-semibold">At a glance</h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {manager && canManage && (
              <Button size="sm" onClick={onCreateAnnouncement}>
                <BellPlus className="h-4 w-4" aria-hidden="true" />
                Create announcement
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={() => onOpenTab('resources')}>
              <BookOpen className="h-4 w-4" aria-hidden="true" />
              Resources
            </Button>
            {manager && (
              <Button size="sm" variant="outline" onClick={() => onOpenTab('students')}>
                <Users className="h-4 w-4" aria-hidden="true" />
                Students
              </Button>
            )}
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <InfoCard label="Current term" value={workspace.semester.target_term ?? 'Not configured'} detail={workspace.semester.title} />
          <InfoCard label="Course status" value={workspace.offering_status} detail={workspace.semester.is_active ? 'Semester is active' : 'Semester is inactive'} />
          <InfoCard label="Enrollment" value={String(workspace.active_enrollment_count)} detail="Active learners" />
          <InfoCard label="Teaching team" value={workspace.authorized_teachers.map((teacher) => teacher.teacher_name).join(', ') || 'No teacher listed'} detail="Authorized teachers" />
        </div>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3">
            <div>
              <CardTitle>Recent announcements</CardTitle>
              <p className="mt-1 text-sm text-[var(--text-muted)]">Latest activity available in this workspace.</p>
            </div>
            <Button size="sm" variant="ghost" onClick={() => onOpenTab('announcements')}>View all</Button>
          </CardHeader>
          <CardContent>
            {workspace.recent_activity.length === 0 ? (
              <EmptyState title="No recent announcements" description="Announcements will appear here when this course has visible activity." />
            ) : (
              <div className="space-y-4">
                {workspace.recent_activity.slice(0, 3).map((item) => (
                  <article key={item.id} className="border-b border-[var(--border)] pb-4 last:border-0 last:pb-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="font-semibold text-[var(--text)]">{item.title}</h3>
                      <AnnouncementBadge value={item.announcement_type} />
                      {item.is_pinned && <Badge variant="secondary">Pinned</Badge>}
                    </div>
                    <div className="mt-2 line-clamp-3"><AnnouncementBody body={item.body} /></div>
                    <p className="mt-2 text-xs text-[var(--text-subtle)]">Updated {activityDate(item)}</p>
                  </article>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Upcoming classes</CardTitle>
            <p className="mt-1 text-sm text-[var(--text-muted)]">Published schedule entries for this offering.</p>
          </CardHeader>
          <CardContent>
            {workspace.upcoming_schedules.length === 0 ? (
              <EmptyState title="No schedule entries" description="No class schedule has been published for this offering yet." action={<Link className="text-sm font-semibold text-[var(--accent-bright)] underline" to={`/schedule?offeringId=${encodeURIComponent(workspace.offering_id)}`}>Open schedule</Link>} />
            ) : (
              <ul className="space-y-3">
                {workspace.upcoming_schedules.map((item) => (
                  <li key={item.id} className="flex flex-col gap-1 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="font-medium">{item.day_of_week}</p>
                      <p className="text-xs text-[var(--text-muted)]">{item.start_time.slice(0, 5)}–{item.end_time.slice(0, 5)}{item.is_lab ? ' · Lab' : ''}</p>
                    </div>
                    <p className="text-sm text-[var(--text-muted)]">{item.room_number ?? 'Room not assigned'}</p>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick actions</CardTitle>
          <p className="mt-1 text-sm text-[var(--text-muted)]">Open the existing academic views with this offering in context.</p>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <QuickActionLink to={`/attendance?offeringId=${encodeURIComponent(workspace.offering_id)}`} icon={<CheckSquare className="h-5 w-5" />} label="Attendance" detail="Review attendance records" />
          <QuickActionLink to={`/schedule?offeringId=${encodeURIComponent(workspace.offering_id)}`} icon={<CalendarDays className="h-5 w-5" />} label="Schedule" detail="Open class routine" />
          <button type="button" className="group rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4 text-left hover:border-[var(--accent-edge)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={() => onOpenTab('announcements')}>
            <BellPlus className="h-5 w-5 text-[var(--accent-bright)]" aria-hidden="true" />
            <span className="mt-3 flex items-start justify-between gap-2"><span><span className="block text-sm font-semibold">Announcements</span><span className="mt-1 block text-xs text-[var(--text-muted)]">Read course updates</span></span><ArrowUpRight className="h-4 w-4 text-[var(--text-subtle)]" aria-hidden="true" /></span>
          </button>
          <button type="button" className="group rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4 text-left hover:border-[var(--accent-edge)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" onClick={() => onOpenTab('assignments')}>
            <BookOpen className="h-5 w-5 text-[var(--accent-bright)]" aria-hidden="true" />
            <span className="mt-3 flex items-start justify-between gap-2"><span><span className="block text-sm font-semibold">Assignments</span><span className="mt-1 block text-xs text-[var(--text-muted)]">Course assignment feed</span></span><ArrowUpRight className="h-4 w-4 text-[var(--text-subtle)]" aria-hidden="true" /></span>
          </button>
        </CardContent>
      </Card>
      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3"><CardTitle>Course events</CardTitle><Button size="sm" variant="ghost" onClick={() => onOpenTab('events')}>View all</Button></CardHeader>
          <CardContent>{workspace.events.length === 0 ? <EmptyState title="No course events" description="Published classes, assessments, and deadlines will appear here." action={<Link className="text-sm font-semibold text-[var(--accent-bright)] underline" to={`/schedule?offeringId=${encodeURIComponent(workspace.offering_id)}`}>Use the course schedule</Link>} /> : <p className="text-sm text-[var(--text-muted)]">{workspace.events.length} upcoming event{workspace.events.length === 1 ? '' : 's'} in this workspace.</p>}</CardContent>
        </Card>
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3"><CardTitle>Course questions</CardTitle><Button size="sm" variant="ghost" onClick={() => onOpenTab('questions')}>View all</Button></CardHeader>
          <CardContent>{workspace.questions.length === 0 ? <EmptyState title="No course questions" description="Students can ask the teaching team from the Questions tab." action={<Button size="sm" variant="outline" onClick={() => onOpenTab('questions')}>Open questions</Button>} /> : <p className="text-sm text-[var(--text-muted)]">{workspace.questions.length} question record{workspace.questions.length === 1 ? '' : 's'} in this workspace.</p>}</CardContent>
        </Card>
      </div>
    </div>
  );
}

function InfoCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-subtle)]">{label}</p>
        <p className="mt-2 break-words font-display text-lg font-semibold capitalize text-[var(--text)]">{value}</p>
        <p className="mt-1 text-xs text-[var(--text-muted)]">{detail}</p>
      </CardContent>
    </Card>
  );
}

function QuickActionLink({ to, icon, label, detail }: { to: string; icon: React.ReactNode; label: string; detail: string }) {
  return (
    <Link to={to} className="group rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4 hover:border-[var(--accent-edge)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]">
      <span className="text-[var(--accent-bright)]">{icon}</span>
      <span className="mt-3 flex items-start justify-between gap-2"><span><span className="block text-sm font-semibold">{label}</span><span className="mt-1 block text-xs text-[var(--text-muted)]">{detail}</span></span><ArrowUpRight className="h-4 w-4 shrink-0 text-[var(--text-subtle)] group-hover:text-[var(--accent-bright)]" aria-hidden="true" /></span>
    </Link>
  );
}

function AnnouncementBadge({ value }: { value: string }) {
  return <Badge variant={value === 'urgent' ? 'danger' : value === 'exam' ? 'secondary' : 'outline'}>{value.replace(/_/g, ' ')}</Badge>;
}
