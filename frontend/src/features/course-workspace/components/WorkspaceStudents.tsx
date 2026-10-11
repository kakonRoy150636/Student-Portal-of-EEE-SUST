import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { getErrorMessage } from '@/lib/errors';
import type { CourseWorkspace } from '@/types/courseWorkspace';
import { teacherAssignmentApi } from '@/features/teacher-assignment/api/teacherAssignmentApi';

export function WorkspaceStudents({ offeringId, workspace, manager }: { offeringId: string; workspace: CourseWorkspace; manager: boolean }) {
  const rosterQuery = useQuery({
    queryKey: ['course-workspace', 'students', offeringId],
    enabled: manager,
    retry: false,
    queryFn: async ({ signal }) => (await teacherAssignmentApi.getRoster(offeringId, signal)).data,
  });

  return (
    <section id="workspace-panel-students" role="tabpanel" aria-labelledby="workspace-tab-students" className="space-y-4">
      <div>
        <p className="kicker">Course membership</p>
        <h2 className="mt-1 font-display text-lg font-semibold">Students</h2>
        <p className="mt-1 text-sm text-[var(--text-muted)]">Active enrollment is reported by the server. Course staff can open the current roster.</p>
      </div>
      {!manager ? (
        <EmptyState title="Roster details are staff-only" description={`This course currently has ${workspace.active_enrollment_count} active learner${workspace.active_enrollment_count === 1 ? '' : 's'}. Your role does not expose individual student records.`} />
      ) : (
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3">
            <div><CardTitle>Enrolled students</CardTitle><p className="mt-1 text-sm text-[var(--text-muted)]">{workspace.active_enrollment_count} active enrollment{workspace.active_enrollment_count === 1 ? '' : 's'}</p></div>
            <Button variant="outline" size="sm" onClick={() => void rosterQuery.refetch()} disabled={rosterQuery.isFetching}>Refresh</Button>
          </CardHeader>
          <CardContent>
            {rosterQuery.isPending && <PageSkeleton cards={0} rows={3} />}
            {rosterQuery.isError && <div className="space-y-3 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-4" role="alert"><p className="font-semibold text-[var(--danger)]">Could not load students.</p><p className="text-sm text-[var(--danger)]">{getErrorMessage(rosterQuery.error, 'Please retry when connected.')}</p><Button variant="outline" onClick={() => void rosterQuery.refetch()} disabled={rosterQuery.isFetching}>Try again</Button></div>}
            {!rosterQuery.isPending && !rosterQuery.isError && (rosterQuery.data ?? []).length === 0 && <EmptyState title="No active students" description="No enrolled students are currently listed for this course." />}
            {!rosterQuery.isPending && !rosterQuery.isError && (rosterQuery.data ?? []).length > 0 && <div className="overflow-x-auto"><table className="w-full min-w-[38rem] text-left text-sm"><thead className="border-b border-[var(--border)] text-xs uppercase tracking-wide text-[var(--text-subtle)]"><tr><th className="px-3 py-3">Student</th><th className="px-3 py-3">Email</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Credits</th></tr></thead><tbody className="divide-y divide-[var(--border)]">{(rosterQuery.data ?? []).map((student) => <tr key={student.student_id}><td className="px-3 py-3"><p className="font-medium">{student.full_name}</p><p className="font-mono text-xs text-[var(--text-muted)]">{student.identifier}</p></td><td className="px-3 py-3 text-[var(--text-muted)]">{student.email}</td><td className="px-3 py-3"><Badge variant="success">{student.status}</Badge></td><td className="px-3 py-3 tabular-nums">{student.credit_hours}</td></tr>)}</tbody></table></div>}
          </CardContent>
        </Card>
      )}
    </section>
  );
}
