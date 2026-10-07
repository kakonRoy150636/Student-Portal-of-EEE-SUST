import React, { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { PageHeader } from '@/components/shared/PageHeader';
import { PageSkeleton } from '@/components/shared/PageSkeleton';
import { EmptyState } from '@/components/shared/EmptyState';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getErrorMessage } from '@/lib/errors';
import type { CourseOffering, TeacherAssignmentRequest, TeacherAssignmentRequestStatus } from '@/types/academic';
import { AdminAssignmentDecisionDialog } from '../components/AdminAssignmentDecisionDialog';
import { AdminOfferingFormDialog } from '../components/AdminOfferingFormDialog';
import { AdminAssignmentRequestTable, AdminCourseOfferingTable } from '../components/AdminAcademicTables';
import {
  useAdminAssignmentRequests,
  useAdminCourseOfferings,
  useAdminCourses,
  useAdminSemesters,
  useApproveAssignmentRequest,
  useCreateCourseOffering,
  usePublishCourseOffering,
  useRejectAssignmentRequest,
  useUnpublishCourseOffering,
  useUpdateCourseOffering,
} from '../hooks/useAdminCourseOfferings';

type RequestFilter = 'all' | TeacherAssignmentRequestStatus;

const requestFilters: Array<{ value: RequestFilter; label: string }> = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'all', label: 'All requests' },
];

export default function AdminAcademicPage() {
  const offeringsQuery = useAdminCourseOfferings();
  const coursesQuery = useAdminCourses();
  const semestersQuery = useAdminSemesters();
  const [requestFilter, setRequestFilter] = useState<RequestFilter>('pending');
  const requestsQuery = useAdminAssignmentRequests();

  const createOffering = useCreateCourseOffering();
  const updateOffering = useUpdateCourseOffering();
  const publishOffering = usePublishCourseOffering();
  const unpublishOffering = useUnpublishCourseOffering();
  const approveRequest = useApproveAssignmentRequest();
  const rejectRequest = useRejectAssignmentRequest();

  const [formOpen, setFormOpen] = useState(false);
  const [editingOffering, setEditingOffering] = useState<CourseOffering | null>(null);
  const [publicationTarget, setPublicationTarget] = useState<CourseOffering | null>(null);
  const [decisionTarget, setDecisionTarget] = useState<TeacherAssignmentRequest | null>(null);
  const [decision, setDecision] = useState<'approve' | 'reject' | null>(null);

  const offerings = offeringsQuery.data ?? [];
  const requests = useMemo(() => {
    const allRequests = requestsQuery.data ?? [];
    return requestFilter === 'all' ? allRequests : allRequests.filter((request) => request.status === requestFilter);
  }, [requestFilter, requestsQuery.data]);
  const courses = coursesQuery.data ?? [];
  const semesters = semestersQuery.data ?? [];
  const queryError = offeringsQuery.error ?? requestsQuery.error ?? coursesQuery.error ?? semestersQuery.error;
  const loading = offeringsQuery.isPending || requestsQuery.isPending || coursesQuery.isPending || semestersQuery.isPending;
  const offeringMutationPending = createOffering.isPending || updateOffering.isPending;
  const publicationMutationPending = publishOffering.isPending || unpublishOffering.isPending;
  const requestMutationPending = approveRequest.isPending || rejectRequest.isPending;
  const anyMutationPending = offeringMutationPending || publicationMutationPending || requestMutationPending;

  const busyOfferingId = publicationMutationPending
    ? (publishOffering.variables ?? unpublishOffering.variables ?? null)
    : null;
  const busyRequestId = approveRequest.isPending
    ? (approveRequest.variables ?? null)
    : rejectRequest.isPending
      ? (rejectRequest.variables?.requestId ?? null)
      : null;
  const decisionError = approveRequest.isError
    ? getErrorMessage(approveRequest.error, 'Could not approve the request.')
    : rejectRequest.isError
      ? getErrorMessage(rejectRequest.error, 'Could not reject the request.')
      : undefined;
  const formError = createOffering.isError
    ? getErrorMessage(createOffering.error, 'Could not create the offering.')
    : updateOffering.isError
      ? getErrorMessage(updateOffering.error, 'Could not update the offering.')
      : undefined;

  const statusCounts = useMemo(() => ({
    // The tabs are filtered client-side, so each count reflects the full queue.
    pending: (requestsQuery.data ?? []).filter((request) => request.status === 'pending').length,
    approved: (requestsQuery.data ?? []).filter((request) => request.status === 'approved').length,
    rejected: (requestsQuery.data ?? []).filter((request) => request.status === 'rejected').length,
  }), [requestsQuery.data]);

  const refresh = () => {
    void offeringsQuery.refetch();
    void requestsQuery.refetch();
    void coursesQuery.refetch();
    void semestersQuery.refetch();
  };

  const openCreate = () => {
    createOffering.reset();
    updateOffering.reset();
    setEditingOffering(null);
    setFormOpen(true);
  };

  const openEdit = (offering: CourseOffering) => {
    createOffering.reset();
    updateOffering.reset();
    setEditingOffering(offering);
    setFormOpen(true);
  };

  const closeForm = (open: boolean) => {
    if (!open && !offeringMutationPending) {
      createOffering.reset();
      updateOffering.reset();
      setFormOpen(false);
      setEditingOffering(null);
    } else {
      setFormOpen(open);
    }
  };

  const submitOffering = (payload: { course_id: string; semester_id: number }) => {
    if (editingOffering) {
      updateOffering.mutate(
        { offeringId: editingOffering.id, data: payload },
        { onSuccess: () => closeForm(false) },
      );
    } else {
      createOffering.mutate(payload, { onSuccess: () => closeForm(false) });
    }
  };

  const confirmPublication = () => {
    if (!publicationTarget) return;
    const target = publicationTarget;
    const mutation = target.publication_status === 'published' ? unpublishOffering : publishOffering;
    mutation.mutate(target.id, { onSuccess: () => setPublicationTarget(null) });
  };

  const openDecision = (request: TeacherAssignmentRequest, nextDecision: 'approve' | 'reject') => {
    approveRequest.reset();
    rejectRequest.reset();
    setDecisionTarget(request);
    setDecision(nextDecision);
  };

  const closeDecision = (open: boolean) => {
    if (!open && !requestMutationPending) {
      approveRequest.reset();
      rejectRequest.reset();
      setDecisionTarget(null);
      setDecision(null);
    }
  };

  const approve = () => {
    if (!decisionTarget) return;
    approveRequest.mutate(decisionTarget.id, {
      onSuccess: () => closeDecision(false),
    });
  };

  const reject = (reason: string) => {
    if (!decisionTarget) return;
    rejectRequest.mutate(
      { requestId: decisionTarget.id, rejectionReason: reason || null },
      { onSuccess: () => closeDecision(false) },
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        kicker="Administration"
        title="Academic management"
        description="Create course offerings, control publication, and review teacher assignment requests."
        action={(
          <div className="flex flex-wrap gap-2">
            <Link to="/admin" className="inline-flex h-10 items-center rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-semibold text-[var(--text)] hover:bg-[var(--surface-muted)]">
              Account approvals
            </Link>
            <Button variant="outline" onClick={refresh} disabled={loading || anyMutationPending}>
              {offeringsQuery.isFetching || requestsQuery.isFetching ? 'Refreshing…' : 'Refresh'}
            </Button>
            <Button onClick={openCreate} disabled={loading || anyMutationPending}>New offering</Button>
          </div>
        )}
      />

      {queryError && (
        <div className="surface space-y-3 p-5" role="alert">
          <p className="font-semibold text-[var(--danger)]">Could not load academic management data.</p>
          <p className="text-sm text-[var(--text-muted)]">{getErrorMessage(queryError, 'Please retry when connected.')}</p>
          <Button variant="outline" onClick={refresh} disabled={loading}>Try again</Button>
        </div>
      )}

      {(createOffering.isSuccess || updateOffering.isSuccess || publishOffering.isSuccess || unpublishOffering.isSuccess || approveRequest.isSuccess || rejectRequest.isSuccess) && (
        <p role="status" className="text-sm text-[var(--success)]">Academic management changes saved.</p>
      )}
      {anyMutationPending && <p role="status" className="text-sm text-[var(--text-muted)]">Saving academic management changes…</p>}

      {loading && <PageSkeleton cards={2} rows={5} />}

      {!loading && !queryError && (
        <>
          <Card>
            <CardHeader className="gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle>Course offerings</CardTitle>
                <p className="mt-1 text-sm text-[var(--text-muted)]">Draft offerings stay hidden from student course selection until published.</p>
              </div>
              <Button size="sm" onClick={openCreate} disabled={anyMutationPending}>New offering</Button>
            </CardHeader>
            <CardContent className="p-0">
              {offerings.length === 0 ? (
                <EmptyState title="No course offerings" description="Create an offering from the course catalogue and an active semester." />
              ) : (
                <AdminCourseOfferingTable
                  offerings={offerings}
                  busyOfferingId={busyOfferingId}
                  onEdit={openEdit}
                  onTogglePublication={setPublicationTarget}
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <CardTitle>Teacher assignment requests</CardTitle>
                  <p className="mt-1 text-sm text-[var(--text-muted)]">Approve requests to assign a teacher and grant roster access.</p>
                </div>
                <div className="flex flex-wrap gap-2" role="group" aria-label="Assignment request status filter">
                  {requestFilters.map((filter) => (
                    <Button
                      key={filter.value}
                      size="sm"
                      variant={requestFilter === filter.value ? 'secondary' : 'outline'}
                      onClick={() => setRequestFilter(filter.value)}
                      disabled={requestMutationPending}
                    >
                      {filter.label}
                      {filter.value !== 'all' && <span className="ml-1 tabular-nums">({statusCounts[filter.value]})</span>}
                    </Button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <AdminAssignmentRequestTable
                requests={requests}
                busyRequestId={busyRequestId}
                onApprove={(request) => openDecision(request, 'approve')}
                onReject={(request) => openDecision(request, 'reject')}
              />
            </CardContent>
          </Card>
        </>
      )}

      <AdminOfferingFormDialog
        open={formOpen}
        offering={editingOffering}
        courses={courses}
        semesters={semesters}
        pending={offeringMutationPending}
        error={formError}
        onOpenChange={closeForm}
        onSubmit={submitOffering}
      />

      <ConfirmDialog
        open={Boolean(publicationTarget)}
        title={publicationTarget?.publication_status === 'published' ? 'Unpublish course offering?' : 'Publish course offering?'}
        message={publicationTarget?.publication_status === 'published'
          ? `${publicationTarget?.course_code} will be removed from published course selection until it is published again.`
          : `${publicationTarget?.course_code} will become visible to eligible students and teachers.`}
        onCancel={() => !publicationMutationPending && setPublicationTarget(null)}
        onConfirm={confirmPublication}
      />

      <AdminAssignmentDecisionDialog
        request={decisionTarget}
        decision={decision}
        pending={requestMutationPending}
        error={decisionError}
        onOpenChange={closeDecision}
        onApprove={approve}
        onReject={reject}
      />
    </div>
  );
}
