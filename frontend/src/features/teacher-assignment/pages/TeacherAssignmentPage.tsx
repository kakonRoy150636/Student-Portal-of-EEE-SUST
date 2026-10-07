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
  const availableQuery = useAvailableOfferings();
  const requestsQuery = useMyAssignmentRequests();
  const requestMutation = useRequestAssignment();
  const [selectedOfferingId, setSelectedOfferingId] = useState<string | null>(null);

  const requestsByOffering = useMemo(
    () => new Map((requestsQuery.data ?? []).map((request) => [request.course_offering_id, request])),
    [requestsQuery.data],
  );
  const rows: TeacherAssignmentRow[] = useMemo(() => (availableQuery.data ?? []).map((offering) => {
    const ownRequest = requestsByOffering.get(offering.id);
    const isAssigned = offering.assigned_teachers.some((teacher) => teacher.teacher_id === user?.id);
    return {
      ...offering,
      ownRequest,
      isAssigned,
      ownStatus: ownRequest?.status ?? offering.request_status ?? (isAssigned ? 'approved' : null),
    };
  }), [availableQuery.data, requestsByOffering, user?.id]);

  const refresh = () => {
    requestMutation.reset();
    void availableQuery.refetch();
    void requestsQuery.refetch();
  };
  const requestAssignment = (offeringId: string) => {
    if (!requestMutation.isPending) requestMutation.mutate(offeringId);
  };
  const selectedOffering = (availableQuery.data ?? []).find((offering) => offering.id === selectedOfferingId);
  const isLoading = availableQuery.isPending || requestsQuery.isPending;
  const hasError = availableQuery.isError || requestsQuery.isError;

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Teaching"
        title="Course assignment"
        description="Request teaching assignments, track approval decisions, and open rosters for your approved courses."
        action={(
          <Button variant="outline" onClick={refresh} disabled={isLoading || requestMutation.isPending}>
            {availableQuery.isFetching || requestsQuery.isFetching ? 'Refreshing…' : 'Refresh'}
          </Button>
        )}
      />

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

      {!isLoading && !hasError && rows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Available course offerings</CardTitle>
            <p className="text-sm text-[var(--text-muted)]">
              Your request status is shown for each offering. Approved assignments unlock the student roster.
            </p>
          </CardHeader>
          <CardContent className="p-0">
            <TeacherAssignmentTable
              rows={rows}
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
    </div>
  );
}
