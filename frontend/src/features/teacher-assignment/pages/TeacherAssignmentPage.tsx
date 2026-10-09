import React, { useMemo, useState } from 'react';
import { EmptyState } from '@/components/shared/EmptyState';
import { PageHeader } from '@/components/shared/PageHeader';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { getErrorMessage } from '@/lib/errors';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  TeacherAssignmentTable,
  TeacherRosterTable,
  type RosterRow,
  type TeacherAssignmentRow,
} from '../components/TeacherAssignmentTable';
import {
  getProvisioningSemesters,
  TeacherCourseOfferingDialog,
} from '../components/TeacherCourseOfferingDialog';
import {
  useProvideCourse,
  useTeacherActiveSemesters,
  useAvailableOfferings,
  useCourseRoster,
  useMyAssignmentRequests,
  useRequestAssignment,
} from '../hooks/useTeacherAssignment';

function RosterPanel({
  offeringId,
  courseCode,
  courseTitle,
  onClose,
}: {
  offeringId: string;
  courseCode: string;
  courseTitle: string;
  onClose: () => void;
}) {
  const rosterQuery = useCourseRoster(offeringId);
  const rows: RosterRow[] = (rosterQuery.data ?? []).map((student) => ({
    ...student,
    id: student.student_id,
  }));

  return (
    <Card>
      <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <CardTitle>{courseCode} roster</CardTitle>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{courseTitle}</p>
        </div>
        <Button variant="outline" size="sm" onClick={onClose}>Close roster</Button>
      </CardHeader>
      <CardContent>
        {rosterQuery.isPending && <PageSkeleton cards={0} rows={3} />}
        {rosterQuery.isError && (
          <div className="space-y-3 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-4" role="alert">
            <p className="font-semibold text-[var(--danger)]">Could not load this course roster.</p>
            <p className="text-sm text-[var(--danger)]">
              {getErrorMessage(rosterQuery.error, 'Please retry when connected.')}
            </p>
            <Button variant="outline" onClick={() => void rosterQuery.refetch()} disabled={rosterQuery.isFetching}>
              Try again
            </Button>
          </div>
        )}
        {!rosterQuery.isPending && !rosterQuery.isError && rows.length === 0 && (
          <EmptyState title="Roster is empty" description="No enrolled students are currently listed for this course." />
        )}
        {!rosterQuery.isPending && !rosterQuery.isError && rows.length > 0 && <TeacherRosterTable rows={rows} />}
      </CardContent>
    </Card>
  );
}

export default function TeacherAssignmentPage() {
  const { user } = useAuth();
  const activeSemestersQuery = useTeacherActiveSemesters();
  const availableQuery = useAvailableOfferings();
  const requestsQuery = useMyAssignmentRequests();
  const requestMutation = useRequestAssignment();
  const provideMutation = useProvideCourse();
  const [selectedOfferingId, setSelectedOfferingId] = useState<string | null>(null);
  const [provideDialogOpen, setProvideDialogOpen] = useState(false);
  const [provideSuccess, setProvideSuccess] = useState(false);

  const requestsByOffering = useMemo(
    () => new Map((requestsQuery.data ?? []).map((request) => [request.course_offering_id, request])),
    [requestsQuery.data],
  );
  const rows: TeacherAssignmentRow[] = useMemo(() => (availableQuery.data ?? []).map((offering) => {
    const ownRequest = requestsByOffering.get(offering.id);
    const isProvided = Boolean(user?.id && offering.created_by === user.id);
    const isAssigned = isProvided || offering.assigned_teachers.some((teacher) => teacher.teacher_id === user?.id);
    return {
      ...offering,
      ownRequest,
      isAssigned,
      isProvided,
      ownStatus: ownRequest?.status ?? offering.request_status ?? (isAssigned ? 'approved' : null),
    };
  }), [availableQuery.data, requestsByOffering, user?.id]);

  const providedRows = useMemo(
    () => rows.filter((row) => row.isProvided),
    [rows],
  );
  const assignmentRows = useMemo(
    () => rows.filter((row) => !row.isProvided),
    [rows],
  );
  const provisioningSemesters = useMemo(
    () => getProvisioningSemesters(activeSemestersQuery.data ?? []),
    [activeSemestersQuery.data],
  );

  const refresh = () => {
    requestMutation.reset();
    provideMutation.reset();
    setProvideSuccess(false);
    void activeSemestersQuery.refetch();
    void availableQuery.refetch();
    void requestsQuery.refetch();
  };
  const requestAssignment = (offeringId: string) => {
    if (!requestMutation.isPending) requestMutation.mutate(offeringId);
  };
  const openProvideDialog = () => {
    provideMutation.reset();
    setProvideSuccess(false);
    setProvideDialogOpen(true);
  };
  const closeProvideDialog = (open: boolean) => {
    if (!open && provideMutation.isPending) return;
    setProvideDialogOpen(open);
    if (!open) provideMutation.reset();
  };
  const provideCourse = (payload: Parameters<typeof provideMutation.mutate>[0]) => {
    if (provideMutation.isPending) return;
    setProvideSuccess(false);
    provideMutation.mutate(payload, {
      onSuccess: () => {
        setProvideDialogOpen(false);
        setProvideSuccess(true);
      },
    });
  };
  const selectedOffering = (availableQuery.data ?? []).find((offering) => offering.id === selectedOfferingId);
  const isLoading = availableQuery.isPending || requestsQuery.isPending;
  const hasError = availableQuery.isError || requestsQuery.isError;

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Teaching"
        title="Course assignment"
        description="Offer your own courses, request teaching assignments, and open rosters for courses you teach."
        action={(
          <Button variant="outline" onClick={refresh} disabled={isLoading || requestMutation.isPending || provideMutation.isPending}>
            {availableQuery.isFetching || requestsQuery.isFetching || activeSemestersQuery.isFetching ? 'Refreshing…' : 'Refresh'}
          </Button>
        )}
      />

      <Card className="border-[var(--accent-edge)] bg-[var(--accent-soft)]/30">
        <CardHeader className="gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Offer a course</CardTitle>
            <p className="mt-1 max-w-2xl text-sm text-[var(--text-muted)]">
              Provide a course directly from this page. It publishes immediately with no separate admin approval, and matching-term students can choose to enroll.
            </p>
          </div>
          <Button size="lg" onClick={openProvideDialog} disabled={provideMutation.isPending || activeSemestersQuery.isPending}>
            Offer a course
          </Button>
        </CardHeader>
        <CardContent>
          {activeSemestersQuery.isPending && (
            <p role="status" className="text-sm text-[var(--text-muted)]">Loading active course-provision semesters…</p>
          )}
          {activeSemestersQuery.isError && (
            <div className="space-y-1 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-3" role="alert">
              <p className="font-semibold text-[var(--danger)]">Could not load course-provision semesters.</p>
              <p className="text-sm text-[var(--danger)]">
                {getErrorMessage(activeSemestersQuery.error, 'Refresh the page and try again.')}
              </p>
            </div>
          )}
          {!activeSemestersQuery.isPending && !activeSemestersQuery.isError && provisioningSemesters.length === 0 && (
            <EmptyState
              title="No course-provision semesters"
              description="An active semester with a target term is required before you can offer a course. Ask an administrator to configure one, then refresh."
            />
          )}
        </CardContent>
      </Card>

      {requestMutation.isError && (
        <div className="space-y-1 rounded-xl border border-[var(--danger)] bg-[var(--danger-soft)] p-4" role="alert">
          <p className="font-semibold text-[var(--danger)]">Could not submit the assignment request.</p>
          <p className="text-sm text-[var(--danger)]">
            {getErrorMessage(requestMutation.error, 'Please refresh the offerings and try again.')}
          </p>
        </div>
      )}
      {requestMutation.isPending && <p role="status" className="text-sm text-[var(--text-muted)]">Submitting assignment request…</p>}
      {requestMutation.isSuccess && (
        <p role="status" className="text-sm text-[var(--success)]">Assignment request submitted and marked pending review.</p>
      )}
      {provideSuccess && (
        <p role="status" className="text-sm text-[var(--success)]">
          Course offered successfully. It is published now, and matching-term students can choose to enroll.
        </p>
      )}

      {isLoading && <PageSkeleton cards={1} rows={5} />}
      {hasError && (
        <div className="surface space-y-3 p-5" role="alert">
          <p className="font-semibold text-[var(--danger)]">Could not load teacher assignments.</p>
          <p className="text-sm text-[var(--text-muted)]">
            {getErrorMessage(availableQuery.error ?? requestsQuery.error, 'Please retry when connected.')}
          </p>
          <Button variant="outline" onClick={refresh} disabled={isLoading}>Try again</Button>
        </div>
      )}

      {!isLoading && !hasError && rows.length === 0 && (
        <EmptyState
          title="No course offerings available"
          description="There are no course offerings available for assignment requests right now."
        />
      )}

      {!isLoading && !hasError && providedRows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Your provided courses</CardTitle>
            <p className="text-sm text-[var(--text-muted)]">
              These courses are published immediately for matching-term students. Open a roster to see enrolled students.
            </p>
          </CardHeader>
          <CardContent className="p-0">
            <TeacherAssignmentTable
              rows={providedRows}
              pendingOfferingId={requestMutation.isPending ? requestMutation.variables ?? null : null}
              onRequest={requestAssignment}
              onRoster={setSelectedOfferingId}
            />
          </CardContent>
        </Card>
      )}

      {!isLoading && !hasError && assignmentRows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Available course offerings</CardTitle>
            <p className="text-sm text-[var(--text-muted)]">
              Your request status is shown for each offering. Approved assignments unlock the student roster.
            </p>
          </CardHeader>
          <CardContent className="p-0">
            <TeacherAssignmentTable
              rows={assignmentRows}
              pendingOfferingId={requestMutation.isPending ? requestMutation.variables ?? null : null}
              onRequest={requestAssignment}
              onRoster={setSelectedOfferingId}
            />
          </CardContent>
        </Card>
      )}

      {selectedOffering && (
        <RosterPanel
          offeringId={selectedOffering.id}
          courseCode={selectedOffering.course_code}
          courseTitle={selectedOffering.course_title}
          onClose={() => setSelectedOfferingId(null)}
        />
      )}

      <TeacherCourseOfferingDialog
        open={provideDialogOpen}
        semesters={activeSemestersQuery.data ?? []}
        semestersLoading={activeSemestersQuery.isPending}
        semesterError={activeSemestersQuery.isError ? activeSemestersQuery.error : undefined}
        pending={provideMutation.isPending}
        error={provideMutation.isError ? provideMutation.error : undefined}
        onOpenChange={closeProvideDialog}
        onSubmit={provideCourse}
      />
    </div>
  );
}
